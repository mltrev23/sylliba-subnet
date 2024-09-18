from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig, pipeline
import torch
import json

def process(messages, source_language, target_language):
    model_id = "meta-llama/Meta-Llama-3.1-8B-Instruct"
    
    quant_config = BitsAndBytesConfig(
        load_in_4bit=True,           # This flag is now part of BitsAndBytesConfig
        bnb_4bit_use_double_quant=True,  # Optional, for double quantization
        bnb_4bit_quant_type="nf4",   # Choose between 'fp4' or 'nf4' (Non-negative quantization)
    )

    # Load the model in 4-bit precision
    model = AutoModelForCausalLM.from_pretrained(
        model_id,
        quantization_config=quant_config,  # 4-bit Quantization config
        torch_dtype=torch.bfloat16,        # Mixed precision (optional, use bfloat16 for efficiency)
        device_map="auto",                 # Automatically map to available GPUs
    )

    # Load the tokenizer
    tokenizer = AutoTokenizer.from_pretrained(model_id)

    get_pipeline = pipeline(
        "text-generation",
        model=model,
        tokenizer=tokenizer,
    )

    response = get_pipeline(messages, max_length = 1000)
    text = response[0]['generated_text'][1]['content']
    print(f'text: {text}')
    content = json.loads(text)
    print(f'content: {content}')
    # input_data = text.split(f"{source_language}:")[1].split(f"{target_language}:")[0]
    # output_data = text.split(f"{target_language}:")[1]
    input_data, output_data = content[source_language], content[target_language]

    return input_data, output_data

if __name__ == 'main':
    messages = """Sylliba is a revolutionary translation module designed to bridge the gap in communication across diverse languages. With the capability to translate many languages, Sylliba supports both audio and text for inputs and outputs, making it a versatile tool for global interactions.
As our first step into the Bittensor ecosystem, Sylliba connects to the network we are building, providing AI tooling and linking various blockchain networks together. Our mission is to create a seamless and intuitive translation experience that leverages advanced AI to foster better understanding and collaboration across different languages and cultures.
Explore Sylliba and experience the future of translation here"""
    source_language = "English"
    target_language = "French"
    input_data, output_data = process(messages, source_language, target_language)
    print(f"input_data: {input_data}")
    print(f"output_data: {output_data}")