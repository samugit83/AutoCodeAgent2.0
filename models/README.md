# AutoCodeAgent Models Integration

AutoCodeAgent provides flexible integration with Large Language Models (LLMs) through both local and cloud-based solutions.
Our agentic framework can communicate with LLM models in two ways:

1. **Local Integration**: Using Ollama to run models directly on your machine using our prebuilt Docker container
2. **Cloud Services**: Connecting to OpenAI's API for access to their hosted models

## Available Models

### Cloud Models
- All OpenAI models are available through the cloud integration
- See the complete list of available models at: https://platform.openai.com/docs/models

### Local Models
- Any model from the [Ollama Model Library](https://github.com/ollama/ollama?tab=readme-ov-file#model-library) can be pulled and used locally

## Advantages: Local vs Cloud Integration

Choosing between local and cloud integration depends on your specific requirements. Here's a breakdown of the benefits for each approach:

### Local Integration (via Ollama)

- **Data Privacy and Security**:
  - Models run on your machine, ensuring sensitive data remains local and is not transmitted over the internet.
- **Cost Efficiency**:
  - Avoid per-request API charges and potentially lower costs for heavy usage.
- **Customization and Flexibility**:
  - Easily fine-tune models and adjust configurations to suit your specific needs.
- **Offline Capability**:
  - Run models without an active internet connection, making it ideal for isolated environments.
- **Full Control**:
  - Manage resource allocation, update cycles, and dependencies directly within your environment.

### Cloud Integration (via OpenAI)

- **Scalability**:
  - Leverage OpenAI's robust infrastructure, which automatically scales to handle varying loads.
- **Access to Latest Models**:
  - Quickly integrate cutting-edge models and receive timely updates from OpenAI.
- **Ease of Setup**:
  - Simplified integration through API calls without the need for local installations or hardware management.
- **Reliability and Uptime**:
  - Benefit from high-availability systems with built-in redundancy and support.
- **Focus on Core Application**:
  - Offload the complexity of model maintenance, allowing you to concentrate on developing your application.



# Local LLM Integration via Ollama

AutoCodeAgent can communicate with LLM models locally using Ollama.
[Ollama](https://ollama.com/) is an open-source project that allows you to run large language models (LLMs) locally on your machine. It provides a simple way to download, run, and manage various open-source models without requiring complex setup or configuration.

### Key Features of Ollama

- **Easy Model Management**: Download and run models with simple commands
- **Local Execution**: Run models entirely on your own hardware
- **API Access**: Interact with models programmatically through a REST API
- **Customization**: Create and modify models with Modelfiles
- **Cross-Platform**: Available for macOS, Windows, and Linux


## Communicating with Ollama

AutoCodeAgent interacts with local LLM models by communicating with the Ollama service. There are several ways to connect to Ollama, depending on your environment and requirements:

### 1. Accessing the API from Within the Docker Network

When your services are running inside Docker, you can use the internal hostname to access the Ollama API. Use the URL: 
```
http://ollama:11434
```

This method is ideal for container-to-container communication within the same Docker Compose network.

### 2. Accessing the API from the Host Machine

If you need to interact with Ollama directly from your local machine (outside of Docker), you can use the host-mapped endpoint:
```
http://localhost:11434
```

This endpoint allows you to make API calls from your development environment, scripts, or external tools, bridging the gap between your local system and the Docker container.

### 3. Direct Command-Line Interaction

Alternatively, you can communicate with Ollama directly via the command line by entering the Docker container. Run the following command to access a bash shell inside the container:

```
docker exec -it ollama_server bash
```

Once inside, you can execute commands to manage models, run tests, or debug issues directly within the container environment.


## Monitoring Ollama Logs

To monitor the logs of the Ollama service in real-time, you can use the following Docker Compose command:
```
docker-compose logs -f ollama
```
This command will display the logs of the Ollama service in real-time, allowing you to see the status of the service and any errors or issues that may occur.


### Assigning a Local Model with Ollama

To assign a local model using Ollama, simply prefix the model name with the string `local_` in the `params.py` file. For example, by setting:

```python
"JSON_PLAN_MODEL": "local_llama3.2:1b"
```

the intellichain will use this model to generate the initial JSON plan when creating subtasks.

**Important:**  
- Use the exact model names as listed in the **Download** column on the [Ollama Model Library](https://github.com/ollama/ollama?tab=readme-ov-file#model-library) page. Final values could be, for instance, `local_deepseek-r1`, `local_llama3.3`, etc.
- Always check the model size on the same page to ensure that your local resources can support the installation of the model.

**Automation Process:**  
The process is completely automated. If you launch the agent and the specified model is not active in Ollama, the system will automatically pull the model from the Ollama repository and start running it to begin handling API requests. Always remember to check the disk space used by Docker after installing a model to avoid overloading your local system resources. You can do this using the command `docker system df`

**Performance Note:**  
The Ollama environment allows you to run LLM models even without a GPU by switching to CPU usage. However, be aware that inference performance will be significantly reduced when running on a CPU.


## Complete API Documentation
For a detailed guide on integrating and using the Ollama API, you can consult the official documentation at the following link: [Ollama API Documentation](https://github.com/ollama/ollama/blob/main/docs/api.md).

### Example: Generate Chat Completion

```bash
curl http://localhost:11434/api/chat -d '{
  "model": "llama3.2",
  "messages": [
    {
      "role": "user",
      "content": "why is the sky blue?"
      "stream": false
    }
  ]
}'
```

### Example: Generate a Completion with Options

 ```bash
 curl http://localhost:11434/api/generate -d '{
  "model": "llama3.2",
  "prompt": "Why is the sky blue?",
  "stream": false,
  "options": {
    "num_keep": 5,
    "seed": 42,
    "num_predict": 100,
    "top_k": 20,
    "top_p": 0.9,
    "min_p": 0.0,
    "typical_p": 0.7,
    "repeat_last_n": 33,
    "temperature": 0.8,
    "repeat_penalty": 1.2,
    "presence_penalty": 1.5,
    "frequency_penalty": 1.0,
    "mirostat": 1,
    "mirostat_tau": 0.8,
    "mirostat_eta": 0.6,
    "penalize_newline": true,
    "stop": ["\n", "user:"],
    "numa": false,
    "num_ctx": 1024,
    "num_batch": 2,
    "num_gpu": 1,
    "main_gpu": 0,
    "low_vram": false,
    "vocab_only": false,
    "use_mmap": true,
    "use_mlock": false,
    "num_thread": 8
  }
}'
```


### Example: List Local Models
```bash
curl http://localhost:11434/api/tags
```

### Example: Pull a Model
```bash
curl http://localhost:11434/api/pull -d '{
  "model": "llama3.2"
}'
```

## Complete Command Line Documentation
For comprehensive information about Ollama's command line interface and available models, refer to the official documentation at: [Ollama Model Library](https://github.com/ollama/ollama?tab=readme-ov-file#model-library).

### Example: Run a Model
```bash 
ollama run llama3.2
```

### Example: Pull a Model
```bash
ollama pull llama3.2
```

### Example: Remove a Model
```bash
ollama rm llama3.2
```

### Example: Show Model Information
```bash
ollama show llama3.2
```


# Model Options

Model options configuration is seamlessly integrated into AutoCodeAgent in a versatile and efficient manner. Ollama provides standardized options across all models, which can be customized through the `/models/models_options.py` file.

To ensure that your model options are correctly applied, verify that the `APPLY_MODEL_OPTIONS` parameter in `params.py` is set to `True`. This parameter controls whether the system will use your custom configurations when interacting with models.

## Why Model Options Matter

The ability to customize model behavior is crucial for achieving optimal results in agent workflows. By adjusting these parameters, you can:

- Control the creativity and randomness of model outputs
- Optimize response length and coherence
- Balance between focused, deterministic responses and more exploratory generations
- Customize memory usage and performance characteristics
- And many more...

These options allow you to tailor the model's behavior to specific tasks, whether you need precise, factual responses for technical questions or more creative outputs for brainstorming sessions.

## Available Options

Below you'll find a detailed explanation of each available option. Understanding these parameters will help you configure models to best suit your specific use cases within the AutoCodeAgent ecosystem.

## mirostat
**What it does:** Controls how the model handles unpredictability (or "perplexity") in its text.

**How to use it:**
- `0`: Mirostat is turned off.
- `1`: Uses the original Mirostat method.
- `2`: Uses an improved version called Mirostat 2.0.

**In simple terms:** Think of it as a tool that decides whether the model should actively adjust its creativity level while generating text.

## mirostat_eta
**What it does:** Determines how fast the model adjusts its behavior based on what it's already generated.

**How to use it:**
- A lower value (e.g., 0.05) makes the adjustments slower and smoother.
- A higher value (e.g., 0.2) makes the model react more quickly to changes.

**In simple terms:** It's like adjusting the sensitivity on a control—small changes lead to gentle responses, while big changes make the model switch gears faster.

## mirostat_tau
**What it does:** Balances between keeping the text consistent and letting it be creative.

**How to use it:**
- A lower tau makes the output more focused and less random.
- A higher tau gives more freedom, resulting in diverse and possibly more surprising text.

**In simple terms:** Imagine a dial where one end makes the text very on-point, and the other lets it wander creatively.

## num_ctx
**What it does:** Sets the size of the "memory" or context window, which is how many previous words or tokens the model considers when creating new text.

**How to use it:**
- A larger number means the model can "remember" more of the conversation or text history.

**In simple terms:** It's like how much context the model can see at once. More context can help it keep track of the conversation better.

## repeat_last_n
**What it does:** Determines how far back the model looks to avoid repeating phrases or words.

**How to use it:**
- A typical value (like 64) tells the model to check the last 64 tokens.
- `0` disables the check, and `-1` makes it check all tokens in the context window.

**In simple terms:** This parameter helps the model avoid sounding repetitive by remembering a set number of recent words.

## repeat_penalty
**What it does:** Applies a penalty if the model is about to repeat something it has already said.

**How to use it:**
- A higher number (e.g., 1.5) means strong discouragement of repetition.
- A lower number (e.g., 0.9) is more forgiving.

**In simple terms:** It's like giving the model a "no repeat" rule—the stronger the rule, the less likely it will repeat itself.

## temperature
**What it does:** Influences how creative or conservative the model's output is.

**How to use it:**
- A higher temperature (e.g., 1.0 or above) leads to more creative, less predictable text.
- A lower temperature (e.g., 0.5) results in more focused and predictable responses.

**In simple terms:** Temperature is like the "spice level" of your text—more spice means more varied, creative output, while less spice means steadier, more expected results.

## seed
**What it does:** Sets the starting point for the random number generator used by the model.

**How to use it:**
- By setting a specific number (like 42), you ensure that the model produces the same output every time for the same prompt.

**In simple terms:** Think of the seed as a recipe's starting point. If you use the same seed, you get the same "flavor" every time you run it.

## stop
**What it does:** Defines specific words or phrases that tell the model when to stop generating text.

**How to use it:**
- When the model encounters the set stop sequence (for example, "AI assistant:"), it will immediately stop producing more words.

**In simple terms:** It acts like a "stop sign" in the conversation, making sure the model doesn't continue beyond what you want.

## num_predict
**What it does:** Sets the maximum number of tokens (words or pieces of words) the model will generate.

**How to use it:**
- A specific number (like 42) limits the output to that many tokens.
- Setting it to `-1` means the model will keep generating tokens indefinitely until stopped.

**In simple terms:** It's a limit for how long the model's answer will be.

## top_k
**What it does:** Limits the pool of potential next tokens to the top "k" most likely choices.

**How to use it:**
- A higher value (like 100) means the model considers more options, leading to more diversity.
- A lower value (like 10) means fewer options are considered, making the output more conservative.

**In simple terms:** Imagine you have a shortlist of words to choose from—the higher the number, the larger the shortlist and the more varied the choices.

## top_p
**What it does:** Works with top_k by filtering tokens based on cumulative probability.

**How to use it:**
- A higher top_p (like 0.95) means the model considers a wider range of words, making the output more diverse.
- A lower top_p (like 0.5) restricts the options, leading to more focused text.

**In simple terms:** It's like saying, "only consider the top portion of all possible words until their combined chance reaches this percentage."

## min_p
**What it does:** Ensures that tokens below a certain probability threshold are filtered out.

**How to use it:**
- For instance, if the most likely token has a probability of 0.9 and min_p is set to 0.05, then any token with a probability less than 0.045 (0.05 × 0.9) won't be considered.

**In simple terms:** It acts as a cutoff so that only tokens with a reasonable chance of being the next word are included, helping balance between quality and variety.

## num_keep
**What it does:** Decides how many tokens from the previous context should be retained when the model's context is updated or trimmed.

**How to use it:**
- A higher value preserves more of the conversation history, helping maintain coherence.
- A lower value allows more new information to be processed within the context window.

**In simple terms:** It helps keep important earlier information in the conversation so that the model doesn't "forget" vital details as new text is generated.

## typical_p
**What it does:** Sets a threshold based on token probabilities so that only tokens with a probability close to a typical or expected value are considered.

**How to use it:**
- Values closer to 1.0 allow for more diverse outputs.
- Lower values (like 0.2) make the output more focused and predictable.

**In simple terms:** It's a way to filter out very unlikely words, striking a balance between safe, predictable choices and creative variety.

## presence_penalty
**What it does:** Penalizes tokens that have already appeared in the conversation, encouraging the model to bring in new words and topics.

**How to use it:**
- Higher values (like 1.5) strongly discourage repetition.
- Lower values (like 0.1) allow more repetition when appropriate.

**In simple terms:** It helps prevent the model from repeating itself by making repeated words less attractive.

## frequency_penalty
**What it does:** Applies a penalty based on how frequently a token appears in the text, reducing overuse of common words.

**How to use it:**
- Higher values (like 1.0) encourage more diverse vocabulary.
- Lower values allow the model to use common words more freely.

**In simple terms:** This makes the text less repetitive by discouraging overused words, fostering more diverse language.

## penalize_newline
**What it does:** If set to True, applies the repetition penalty even to newline characters.

**How to use it:**
- Set to True to prevent excessive line breaks.
- Set to False if you want the model to format text with natural paragraph breaks.

**In simple terms:** It helps prevent the model from inserting too many line breaks, keeping the text flow smoother.

## numa
**What it does:** A flag for enabling NUMA (Non-Uniform Memory Access) optimizations on systems that support it.

**How to use it:**
- Set to True on multi-processor systems with NUMA architecture.
- Leave as False on standard desktop or laptop computers.

**In simple terms:** When True, it can improve performance on systems with a NUMA architecture by better managing memory access.

## num_batch
**What it does:** Determines the number of tokens or prompts to process together in one batch.

**How to use it:**
- Higher values can improve throughput but require more memory.
- Lower values are better for systems with limited resources.

**In simple terms:** It groups processing tasks, which can improve efficiency and speed during text generation.

## num_gpu
**What it does:** Specifies how many GPU devices to use for the model's computations.

**How to use it:**
- Set to the number of GPUs you want to utilize (e.g., 2 for two GPUs).
- Set to 0 to use CPU only.

**In simple terms:** If you have multiple GPUs, this tells the model to use them to speed up generation.

## main_gpu
**What it does:** Designates which GPU should be treated as the primary one during processing.

**How to use it:**
- Specify the index of your preferred GPU (e.g., 0 for the first GPU).
- Particularly useful in multi-GPU setups.

**In simple terms:** When using more than one GPU, this parameter picks the "lead" GPU for handling most of the work.

## low_vram
**What it does:** Optimizes the model for systems with low video memory (VRAM).

**How to use it:**
- Set to True if you have a GPU with limited memory.
- Keep as False on high-end GPUs for better performance.

**In simple terms:** When True, it makes adjustments so that the model runs more efficiently on GPUs that don't have a lot of memory, though it might affect performance.

## vocab_only
**What it does:** When enabled, loads only the vocabulary (word list) without the full model weights.

**How to use it:**
- Primarily used for development or debugging purposes.
- Not typically needed for normal model usage.

**In simple terms:** This can be useful for debugging or special cases where you don't need the entire model loaded.

## use_mmap
**What it does:** Tells the model to use memory mapping to load files, which can help manage RAM usage and speed up file access.

**How to use it:**
- Generally best left as True for most use cases.
- Set to False if you experience specific issues with memory mapping.

**In simple terms:** It's like reading parts of a big book on demand instead of loading the entire book into memory at once.

## use_mlock
**What it does:** When True, locks the model's memory in RAM to prevent it from being swapped out.

**How to use it:**
- Set to True for more consistent performance, especially on systems with enough RAM.
- Set to False if you have limited RAM and need to conserve memory.

**In simple terms:** This can improve performance by keeping important data always in fast-access memory, though it might use more system resources.

## num_thread
**What it does:** Sets the number of CPU threads to use during text generation.

**How to use it:**
- Set to the number of available CPU cores for maximum performance.
- Lower values can be used to leave resources for other applications.

**In simple terms:** More threads can mean faster processing, as the work is shared across multiple CPU cores.
