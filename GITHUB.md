# Using GitHub with Codex

This guide explains how to let Codex work on your GitHub projects directly, so you never have to make an archive and upload it again. Codex downloads the code itself, works on it, and sends the changes back to GitHub, and then you get them on your laptop with a normal `git pull`. Everything is done from the Codex website, so you do not need SSH access to the server.

## 1. How it works

Your GitHub account never goes on the server. Instead, every project gets its own key, called a deploy key, and that key only opens that one repository. If someone ever got hold of it, they could reach that single project and nothing else on your account, and you can cancel it from GitHub in a few seconds.

The keys are stored inside the website's encrypted database. When the website starts, it unlocks them into a folder that lives only in the server's memory, so they are never written to the disk in plain form, and they disappear when the server shuts down.

The address of the repository is a little different from the one GitHub shows you. Instead of `git@github.com:yourname/myproject.git` you use `git@github-myproject:yourname/myproject.git`, and that small change is what tells the server which key to use. The website shows you the right address, so you do not have to build it yourself.

## 2. Before you start

You need a repository on GitHub that you own or can manage, because adding a deploy key needs access to the repository settings. You also need to be signed in to the Codex website.

## 3. Adding a project

Adding a project has two parts. First the website creates the key, then you give the public half of it to GitHub.

### 3.1 Creating the key on the website

Open the Codex website and select Repositories in the main menu. The Add a repository section has two fields.

Short name: a name of your choice, using lowercase letters, digits and hyphens, for example `myproject`. It becomes part of the address Codex uses.
GitHub repository: the owner and name of the repository, for example `yourname/myproject`. Alternatively, paste the address of the repository straight from your browser, such as `https://github.com/yourname/myproject`, and the website works out the rest.

Select Create key. The page reloads and announces that the key was created, followed by numbered steps for GitHub.

### 3.2 Adding the key on GitHub

The steps on the page are the same as the ones below, so you can follow whichever is easier.

1. Select Copy public key. The key starts with `ssh-ed25519`, and it is safe to copy and paste, because it can only be used to check the key, not to unlock anything.
2. Select the link to the page for adding a deploy key. It opens the right page of your repository on GitHub in a new tab, so you do not have to find it in the settings.
3. In Title, write something you will recognise later, for example `codex server`. In Key, paste the public key.
4. Tick Allow write access if you want Codex to send changes back. Without it, Codex can only download the code.
5. Select Add key. GitHub may ask for your password or a confirmation code at this point.

The key works straight away, so you can go back to the Codex tab and start a task.

## 4. Working with Codex

You talk to Codex in the task box on the Tasks page, the same as before. The only thing to remember is to give it the special address, which you can copy with the Copy address button on the Repositories page.

The first time you work on a project, Codex needs to download it. A good first task looks like this:

"Clone git@github-myproject:yourname/myproject.git, then fix the bug where the settings menu does not save. Commit the change on main and push it."

The next times, the project is already in the working folder, so you can start from it:

"In the myproject folder, pull the latest changes on main. Then add a volume option to the settings menu, commit it on main and push it."

Asking Codex to pull first matters, because you may have pushed changes of your own since its last task. Without the pull, its push would be refused.

Codex works directly on main, so its changes reach your main code as soon as it pushes them. To get them on your computer, you do not need to clone again. Run `git pull` in the folder you already cloned, or let Codex Desktop do it for you after every task. Section 4 of README.md explains how to set that up.

If you ever want to look at a change before it reaches main, ask Codex to push it on a new branch instead, for example "commit it on a new branch called volume-option and push the branch". On GitHub you can then open a pull request from that branch, read exactly what changed, and merge it only if you are happy with it.

The commits that Codex makes appear under the name Codex, so you can always tell its changes apart from yours.

## 5. Managing projects

The Your repositories section of the Repositories page lists every project that has a key. Each one has the following.

Repository and address: the GitHub repository it belongs to, and the address Codex should use for it.
Public key: a collapsed section that shows the public key again, in case you need to add it to GitHub a second time.
Deploy keys link: opens the deploy keys page of that repository on GitHub, in a new tab.
Remove key: deletes the key from the server straight away. After that, also delete it on GitHub, using the deploy keys link, so it cannot be used anywhere.

Removing a key does not delete the project folder from the working folder. If you want that gone too, ask Codex to delete it.

## 6. Things to know

Write access: a key with write access lets Codex push to any branch of that repository, and because Codex works on main, a task it misunderstands also lands on main straight away. Every change stays in the Git history, though, so you can always ask Codex to undo a commit. Do not turn on branch protection for main that requires pull requests, because it would refuse every push from Codex.
Your website password: anyone who signs in to the Codex website can create keys and use them through Codex. This is one more reason to keep a long password, and to consider the optional second password in front of the site.
Codex can see the repository keys: Codex runs on the server as its own user, separate from the website, so it cannot read the website's database or the key that unlocks it. It can read the unlocked repository keys, though, because it needs them to reach GitHub, and this is why each key only opens one repository.
One key per repository: GitHub does not allow the same deploy key on two repositories, which is why every project gets its own.
Private repositories: deploy keys work the same way for private and public repositories.
The plain ssh command: running `ssh -T github-myproject` by hand inside a task does not work, because the special addresses are only set up for Git. Git commands such as clone, pull and push work normally, and they are all you need.

## 7. If something goes wrong

Most problems show up as a message from Git in the Codex answer. I will list the common ones with what they mean.

Permission denied (publickey): GitHub did not accept the key. Usually the key was not added to the repository yet, or it was added to a different repository.
The key you are authenticating with has been marked as read only: the key works, but Allow write access was not ticked. Edit the key on GitHub, or remove it and add it again with the box ticked.
Repository not found: the owner or the repository name in the address is wrong, or the key belongs to a different repository. Check the address on the Repositories page.
Could not resolve hostname github-myproject: the short name in the address does not match any project on the Repositories page. Check the spelling, or copy the address again with the Copy address button.

If you get stuck, copy the error message from the Codex answer and send it to me.
