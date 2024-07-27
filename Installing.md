### Requirements

This software requires a VPS with with a minimum of 1 core (2 cores is heavily recomended), 1 gig of RAM (4
recomended), 2 gigs of swap, 40 gigs of SSD storage. This software was developed for the intention of using
a VPS to its fullest extent. If you wish to use a virtual environment, please consult your VPS
documentation. 

If you choose to use Ollama as your AI engine, you will need a GPU for best performance. While the
**tinyllama** model will work reasonable well without a GPU, there is a severe performance penality for the
bot being able to respond to user requests.


### Dependencies:

Companion requires Python 3 (version 3.8.10) and pip3. If you don't have python3 installed you can run the following commands on Debian/Ubuntu

```bash
    apt get install python3 python3-pip -y
```

### Installing and setting up

Clone the repo:

```bash
git clone https://github.com/rapmd73/Companion.git
```
This will clone the repo to a folder called Companion in your current directory.


Install the dependencies

```bash
    pip3 install -r requirements.txt
```

### .env Configuration

You must provide your bot's token and an OpenAI API Key if utilizing OpenAI. A sample .env is provided and as such you can edit it by running:

```bash
    nano .env.sample
```
Save with Ctrl+S and exit with Ctrl+X
Rename the file to .env

```bash
    mv .env.sample .env
```

## Ollama Local LLM

Install Ollama with the following script

```bash
    curl -fsSL https://ollama.com/install.sh | sh
```

Pull a model from Ollama

```bash
    ollama pull tinyllama
```

In systems were systemd isn't available, you need to run start ollama in a separate terminal utilizing the following command:
```bash
    ollama serve
```

Otherwise you can run:
```bash
    sudo systemctl enable ollama
    sudo systemctl start ollama
```

### Start the script

```bash
 ./Companion.py
```
or
```bash
python3 Companion.py
```

## Reboot startup

For Companion to auto start after a reboot, the following line needs to be added to your crontab. **It is
absolutely critical that you are root user or run crontab with sudo privileges. Companion must be in the crontab
root level to work correctly**.

This case assumes /Companion folder is in your user directory simply replace user with your actual username.

```crontab
@reboot ( home/USER/Companion.py & ) > /dev/null 2>&1
```