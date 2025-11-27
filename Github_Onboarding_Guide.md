## Welcome to the xCommand Cloud Development Team

This guide explains everything you need to start contributing safely to the project.
Our entire development workflow is GitHub-centric, which means **GitHub is the only source of truth** for local development and server deployment.

Follow these steps and you’ll stay perfectly in sync with the system.

---

## 1. Access You Need

### GitHub

You’ll be added as a collaborator to the repo:

```
https://github.com/vulkanCommand/xcommand-n8n-rental
```

This gives you:

* Ability to clone the project
* Create branches
* Push changes directly to main (if approved)
* Open pull requests

If you don’t have a GitHub account, create one before proceeding.

---

## 2. Clone the Project

Once granted access, clone it locally:

```bash
git clone https://github.com/vulkanCommand/xcommand-n8n-rental.git
cd xcommand-n8n-rental
```

You’ll find two helper scripts inside the repo:

* `update.sh`
* `gitpush.sh`

These are required for how we sync code.

---

## 3. Daily Workflow (Very Important)

### Before you write any code:

```
./update.sh
```

This script:

* Pulls the latest changes from GitHub
* Makes sure you’re up-to-date
* Stops you from overwriting someone else’s work

### After you finish coding:

```
./gitpush.sh
```

This script:

* Shows your current git status
* Stages your changes
* Asks for a commit message
* Pushes everything to `origin/main`

**If your code isn’t pushed to GitHub, the server will never get it.**

---

## 4. Deployment (Who Handles It)

Deployment is **not done by teammates**.
The production server only deploys from GitHub using:

```
./deploy.sh
```

This is handled by the DevOps lead (Kalyan).

Never deploy directly from your machine.
Never copy files into the server manually.

---

## 5. Server Access (Optional)

Most developers do **not** need server access.

If required, you will be given an SSH account with **restricted permissions**:

* You can read deployment logs
* You can inspect containers
* You cannot modify production files
* You cannot run dangerous commands

All code changes must go through GitHub.

---

## 6. Rules That Must Be Followed

1. **Never edit files directly on the server.**
   The server is read-only. All edits must happen locally and be pushed to GitHub.

2. **Always run `update.sh` before coding.**
   This ensures you start from the latest version.

3. **Always run `gitpush.sh` after coding.**
   This ensures your changes don’t get lost.

4. **Never push broken code to main.**
   Test locally first.

5. **Don’t create random branches unless needed.**
   Use:

   ```
   main
   feature/<name>
   hotfix/<name>
   ```

6. **If you’re unsure, ask before deploying.**

---

## 7. Tools You Will Need

* Git Bash or terminal
* Docker / Docker Compose (for local testing)
* VS Code or any editor you prefer

Optionally:

* GitHub Desktop (if you prefer GUI)
* Postman (API testing)

---

## 8. Quick Start Checklist

Before your first day:

* [ ] Accept GitHub repo invitation
* [ ] Clone the repo
* [ ] Verify `./update.sh` runs
* [ ] Verify `./gitpush.sh` runs (with a test file)
* [ ] Make sure Docker is installed (optional)
* [ ] Read this onboarding file fully

After that, you're ready to build features.

---

## 9. Need Help?

Ping the maintainer (Durga Kalyan) for:

* Access issues
* GitHub permission problems
* Deploy failures
* Local environment setup

We keep communication direct, simple, and fast.

---

# **End of Onboarding**

Welcome to the team — build responsibly and push confidently.

Just tell me what you want next.
