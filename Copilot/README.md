To start this examples I need to go to python virutal environment
    source ../.venv/bin/activate
if all is ok you will see (.venv) in front of command like
    To go out of venv - just type deactivate

Then we need to login to github, type in command:
    copilot login 

    -- You will need to go to github na login 

Then run 
    python3 <file.py>


History:
    I have created virutal environment with 
        python3 -m venv .venv
    
    Then went to venv with:
        source .venv/bin/activate
    
    Installed copilot-sdk with :
        pip install github-copilot-sdk