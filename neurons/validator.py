# The MIT License (MIT)
# Copyright © 2023 Yuma Rao
# TODO(developer): Set your name
# Copyright © 2023 <your name>

# Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated
# documentation files (the “Software”), to deal in the Software without restriction, including without limitation
# the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software,
# and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

# The above copyright notice and this permission notice shall be included in all copies or substantial portions of
# the Software.

# THE SOFTWARE IS PROVIDED “AS IS”, WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO
# THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL
# THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
# OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
# DEALINGS IN THE SOFTWARE.

import asyncio
import time
import os
import requests
import random
# Bittensor
import bittensor as bt

# import base validator class which takes care of most of the boilerplate
from sylliba.base.validator import BaseValidatorNeuron
# Bittensor Validator Template:
from sylliba.validator import forward
from neurons.config import validator_config
from sylliba.protocol import ValidatorRequest
from module_validator.modules.translation.translation import Translation
from module_validator.modules.translation.data_models import TranslationRequest
from dotenv import load_dotenv
from sylliba.validator import reward

load_dotenv()

TASK_STRINGS = [
    "text2text"
]

TARGET_LANGUAGES = [
    "English",
    "French",
    "Spanish",
    "German",
    "Italian"
]

TOPICS = [
    "Time travel mishap",
    "Unexpected inheritance",
    "Last day on Earth",
    "Secret underground society",
    "Talking animal companion",
    "Mysterious recurring dream",
    "Alien first contact",
    "Memory-erasing technology",
    "Haunted antique shop",
    "Parallel universe discovery"
]

translation = Translation()
        

class Validator(BaseValidatorNeuron):
    """
    Your validator neuron class. You should use this class to define your validator's behavior. In particular, you should replace the forward function with your own logic.

    This class inherits from the BaseValidatorNeuron class, which in turn inherits from BaseNeuron. The BaseNeuron class takes care of routine tasks such as setting up wallet, subtensor, metagraph, logging directory, parsing config, etc. You can override any of the methods in BaseNeuron if you need to customize the behavior.

    This class provides reasonable default behavior for a validator such as keeping a moving average of the scores of the miners and using them to set weights at the end of each epoch. Additionally, the scores are reset for new hotkeys at the end of each epoch.
    """

    def __init__(self, config=None):
        super(Validator, self).__init__(config=validator_config())
        self.total_miners = len(self.metagraph.uids)
        self.validated = set()
        self.batch_size = 50
        self.current_index = 0
        self.current_batch = self.get_batch(self.batch_size)
        bt.logging.info("load_state()")
        self.now = time.time()
        self.load_state()
        
    def process(self, synapse_query):
        bt.logging.info(f"synapse_query:{synapse_query}")
        try:
            return translation.process(synapse_query)
        except Exception as e:
            bt.logging.error(f"Error processing translation request {e}. \n{synapse_query}")
            return ""

    def get_batch(self, batchsize):
        batch = []
        for _ in range(batchsize):
            if len(self.validated) == self.total_miners:
                self.reset()
                
            while self.current_index in self.validated:
                self.current_index = (self.current_index + 1) % self.total_miners
            self.validated.add(self.current_index)
            batch.append(self.current_index)
            self.current_index = (self.current_index + 1) % self.total_miners
        return batch
    
    def reset(self):
        self.validated.clear()
        self.current_index = 0
    
    def get_progress(self):
        return f"{len(self.validated)}/{self.total_miners} miners validated"
                
    async def forward(self):
        source_language = "English"
        target_language = random.choice(TARGET_LANGUAGES)
        task_string = random.choice(TASK_STRINGS)
        topic = random.choice(TOPICS)
        # Generating the query
        successful = []
        sample_request = self.generate_query(target_language, source_language, task_string, topic)
        # bt.logging.info(f"sample_request: {sample_request}")
        reference_set = self.process(sample_request)
        # Querying the miners
        # axons = [axon for axon in self.metagraph.axons if axon.uid in self.validated] 
        # axons = self.metagraph.axons
        axons = [self.metagraph.axons[10]]
        bt.logging.info(f"axons:{axons}")
        # try:
        for i in range(6):
            batch = self.get_batch(self.batch_size)
            responses = self.dendrite.query(
                axons,
                sample_request
            )
            bt.logging.info(f"")
            bt.logging.info(f"responses:{responses}")
            # Getting the responses
            for j in len(responses):
                if responses[j].success:
                    successful.append(responses[j].data, batch[i])
                else:
                    bt.logging.warning(f"Miner {batch[i]} failed to respond.")
        # except Exception as e:
        #     bt.logging.error(f"Failed to query miners with exception: {e}")
        # Rewarding the miners
        results = []
        for i in range(len(successful)):
            results.append(successful[i][1], self.process_validator_output(successful[i][0], reference_set))
            # Updating the scores
            self.update_scores(results[i][0], results[i][1])
        # Set weights
        self.now = time.time()
        if self.now % 10 == 0:
            self.set_weights()
        return await forward(self)
        
    def process_validator_output(self, reference_set, validator_output):
        return reward(query=reference_set, response=validator_output)
    
    def generate_query(self, target_language, source_language, task_string, topic):
        url = os.getenv("INFERENCE_URL")
        token = os.getenv("INFERENCE_API_KEY")
        bt.logging.info(token)
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {token}'
        }
        body = {
            "messages": [
                {
                    "role": "system",
                    "content": f"You are an expert story teller. You can write short stories that capture the imagination, send readers on an adventure and complete an alegorical thought all within 100 words. Please write a short story about {topic}. Keep the story short but be sure to use an alegory and complete the idea. This story will be translated into {target_language} so use any relevant cultural ideas or contexts but be sure to write the story in English."
                }
            ],
            "model": "gpt-4o"
        }
        response = requests.post(url, headers = headers, json = body, timeout=30)
        bt.logging.info(f"openairesponse:{response.json()}")
        
        return TranslationRequest(data = {
                    "input": response.json()["choices"][0]["message"]["content"],
                    "task_string": "text2speech",
                    "source_language": "English",
                    "target_language": "English"
                })



# The main function parses the configuration and runs the validator.
if __name__ == "__main__":
    # validator = Validator()
    # validator.run()
    
    with Validator() as validator:
        while True:
            bt.logging.info(f'validator running ... {time.time()}')
            time.sleep(5) 
