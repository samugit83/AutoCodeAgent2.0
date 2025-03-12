

# Hugging Face Transformers Integration
This directory contains examples of how to use Hugging Face's Transformers library with AutoCodeAgent.

## Setup Environment

```bash

# Install Python environment
sudo apt-get update
sudo apt-get install python3-venv
python3 -m venv myenv
source myenv/bin/activate

# Install PyTorch
pip install torch

# Install Transformers
pip install transformers

# Install Accelerate
pip install accelerate 

# Install BitsAndBytes
pip install transformers accelerate bitsandbytes>0.37.0

# Install NVIDIA driver for GPU acceleration if the ami is not deeplearning
sudo apt install nvidia-driver-535 

# Install Hugging Face CLI to allow model downloads
pip install huggingface_hub
huggingface-cli login

```


## Loading Models

### Loading a Randomly Initialized Model (Not Pre-trained)

You can create a model with a default configuration that is randomly initialized:

```python
from transformers import BertConfig, BertModel

config = BertConfig()
model = BertModel(config)
```

### Loading a Pre-trained Model

You can load a pre-trained model directly from the Hugging Face Hub:

```python
from transformers import BertModel

model = BertModel.from_pretrained("bert-base-cased")
```
