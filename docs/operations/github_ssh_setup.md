GitHub SSH setup for stable non-interactive push
================================================

Goal
----
Use SSH instead of HTTPS for the serdes-coding repository so Codex can push
without waiting for GitHub credential-manager prompts.

Step 1: Create an SSH key
-------------------------
Run in PowerShell:

    ssh-keygen -t ed25519 -C "johnny13816@gmail.com"

When asked for the file location, press Enter to use the default path:

    C:\Users\johnn\.ssh\id_ed25519

When asked for a passphrase:

    Recommended for Codex automation: press Enter and leave it empty.

Using a passphrase is more secure, but it may still require manual input during
push, which defeats the goal of non-interactive Codex push.

Step 2: Copy the public key
---------------------------
Run in PowerShell:

    Get-Content $env:USERPROFILE\.ssh\id_ed25519.pub

Copy the full output line. It should start with:

    ssh-ed25519

Step 3: Add the key to GitHub
-----------------------------
Open GitHub:

    GitHub -> Settings -> SSH and GPG keys -> New SSH key

Use:

    Title: desktop-codex-serdes
    Key type: Authentication Key
    Key: paste the public key from Step 2

Then click:

    Add SSH key

Step 4: Test GitHub SSH authentication
--------------------------------------
Run in PowerShell:

    ssh -T git@github.com

The first time, SSH may ask:

    Are you sure you want to continue connecting?

Type:

    yes

Success looks similar to:

    Hi johnny13816-max! You've successfully authenticated...

Step 5: Change the repository remote to SSH
-------------------------------------------
Run in PowerShell:

    cd "C:\Users\johnn\OneDrive\文件\Serdes-learn\serdes-coding"
    git remote set-url origin git@github.com:johnny13816-max/serdes-coding.git

Confirm:

    git remote -v

Expected output:

    origin  git@github.com:johnny13816-max/serdes-coding.git (fetch)
    origin  git@github.com:johnny13816-max/serdes-coding.git (push)

Step 6: Test push
-----------------
Run in PowerShell:

    git push origin main

If there is no new commit, success may look like:

    Everything up-to-date

After this setup, Codex should be able to push using:

    "C:\Program Files\Git\cmd\git.exe" push origin main

