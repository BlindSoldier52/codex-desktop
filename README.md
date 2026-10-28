# Codex Desktop

Codex Desktop lets you use Codex on your server from a normal Windows window, without opening the website. It does everything the website does, and it can also send a whole folder of code in one go, download a folder as a zip file, and tell you with a sound and a notification when Codex finishes a task.

## 1. Starting the app

Codex Desktop is a single file, so you do not need to install anything. Extract the `CodexDesktop.zip` package anywhere you like, open the `CodexDesktop` folder, then open `CodexDesktop.exe`, and the app starts. You can also copy the exe file somewhere else on its own, for example to your desktop, because it does not need the other files to run.

The package contains three files, so I will just list them.

CodexDesktop.exe: the app itself.
README.md: this guide.
GITHUB.md: the guide for letting Codex work on your GitHub projects.

The file is not digitally signed, so the first time you open it Windows may show a blue SmartScreen window saying that it protected your computer. Select More info, then Run anyway. Windows remembers this, so it only happens once.

## 2. Pairing the computer

Before the app can reach Codex, the computer must be paired with the server. You only do this once.

1. Open the Codex website, sign in, and select Devices in the main menu.
2. Select Create pairing code. The page shows a code of 20 characters, in groups of four, with a Copy code button. The code works only once and expires after 10 minutes.
3. Open Codex Desktop. Because the computer is not paired yet, it opens the pairing window.
4. In Pairing code, type or paste the code. The hyphens are optional, and lowercase letters are fine.
5. In Name for this computer, keep the suggested name or write your own. This is the name you will see on the Devices page.
6. Select Pair.

The main window opens, and from now on the app remembers that the computer is paired. The pairing is saved encrypted by Windows, so it only works for your Windows account on this computer. If someone copies the file to another computer or another account, it does not work there.

## 3. The main window

The main window has six tabs. Press Control Tab to move between them. Every field and list has a shortcut, shown as an underlined letter, so Alt and that letter jumps straight to it.

### 3.1 Tasks

This tab is where you talk to Codex. It contains the following.

Task for Codex: the box where you write what Codex should do. Alt T jumps here.
Continue the previous conversation: when this is ticked, Codex remembers what you wrote in the earlier tasks of the conversation, so you can answer it or ask for more without repeating yourself. Untick it to start a new conversation, where Codex knows nothing about earlier tasks. It is ticked at the start and again after each task, so the next task continues the new conversation. Alt N.
Submit task: sends the task. Alt S. While a task runs, this button is unavailable, because Codex works on one task at a time.
Stop task: stops the task that is running. Alt O.
Codex answer: the answer, which grows as Codex works. Alt A jumps here, and you can read it with the arrow keys like any text.
Previous tasks: the last 20 tasks. Select one and press Enter, or double-click it, to open a window with its details: the status with the times it was submitted and finished, and which task it continued if it was part of a conversation, then your request and the Codex answer. The window opens on the answer, so you can read it straight away, and Escape closes it. If the task is still running, Enter moves you to the Codex answer box instead, where the answer keeps growing. Alt P.
Refresh previous tasks: reloads the list. Alt R.

When a task finishes, the app plays a sound and shows the result in the status bar. If the window is not active, it also shows a Windows notification, so you can do something else while Codex works. If you added local projects in the Settings tab, the app then also brings the new changes from GitHub into them, as explained in section 4. If you close the app while a task runs, the task keeps running on the server, and the app follows it again the next time you open it.

The answer box does not read new text aloud by itself, because Windows boxes do not announce text added to them. Instead, wait for the sound at the end, or move to the box and read what is there so far.

### 3.2 Files

This tab shows the files in the working folder on the server, with their sizes, and has these buttons.

Refresh: reloads the list.
Download file: downloads the selected file to a place you choose.
Download folder of the selected file: downloads the folder that contains the selected file, as a zip file. The app shows the folder path first, so you can shorten it to download a bigger folder.
Download everything: downloads the whole working folder as a zip file.
Upload file: sends one file of up to 20 GB. If it is a zip or tar archive, the server extracts it into a new folder, the same as the website does.
Upload folder: sends a whole folder from your computer, with all its subfolders, into a folder with the same name on the server. Files that already exist there are replaced, so you can send an updated version of a project the same way. Archives inside the folder are not extracted, so your project stays exactly as it is. The folders `__pycache__`, `node_modules`, `.venv`, `venv`, `.mypy_cache` and `.pytest_cache` are skipped, because they are large and can be rebuilt.

Uploads and downloads show a progress window, which you can cancel.

### 3.3 Repositories

This tab manages the GitHub keys, the same as the Repositories page on the website. The GitHub guide in GITHUB.md explains how they work and how to give Codex tasks for your projects.

Add repository: asks for a short name and the GitHub repository, then shows the public key and the address for Codex, with buttons to copy them and to open the right GitHub page.
Show key and address: shows the same window again for the selected repository.
Remove key: deletes the key of the selected repository from the server, then offers to open the GitHub page so you can delete it there too.

### 3.4 Log

This tab shows the same log as the website, newest first, with sign-ins, tasks, uploads and device changes. Select Refresh to reload it.

### 3.5 Usage

This tab shows how much of the ChatGPT account limits Codex has used, the same as the Usage page on the website. The app checks them again every time you open the tab, so they are always fresh. Every task uses part of the limits, and longer tasks, higher thinking levels and Fast speed use more.

Usage limits: a box you can read with the arrow keys, with one line for each limit. Alt U. An example looks like this.

5-hour limit: 22% used, 78% left. It resets on Wednesday 28 October at 02:31, in 2 hours and 9 minutes.
Weekly limit: 7% used, 93% left. It resets on Tuesday 03 November at 03:23, in 6 days and 3 hours.
Plan: ChatGPT Plus.

Refresh: checks the limits again. Alt R.

Codex has two limits on a Plus account. The 5-hour limit is a short window, so if you use it up, you only wait a few hours. The weekly limit is the bigger one, and when it is used up, Codex stops until it resets. There is no daily limit. If a limit is reached, the tab says so on the first line. If you have credits or reset credits on your account, it shows them too.

### 3.6 Settings

This tab has the same settings as the Settings page on the website, and changing them in one place changes them in the other. The lists of models and thinking levels come from Codex on the server, so they stay up to date when OpenAI adds new models. Every list starts with a default choice, which leaves the decision to Codex.

Show technical details in Codex answers: when this is ticked, the answer also shows the session number, the commands Codex runs with their output, and the number of tokens used. When it is not ticked, you only see what Codex writes to you, and errors. Alt D.
Model: the model Codex uses for new tasks. Alt M.
Thinking level: how long the model thinks before it answers. Higher levels are slower and use more of your usage limit. Not every model supports every level, and saving tells you if the chosen model does not. Alt T.
Speed: Standard or Fast. Fast answers about 1.5 times faster, and on some models it also uses more of your usage limit. Alt P.
Thinking summaries: short summaries of how Codex thinks, which you only see when technical details are shown. Alt U.
Answer length: how long and detailed the answers are. Alt L.
Personality: the tone Codex uses when it writes to you. Alt N.
Save settings: saves everything on the server. Alt S.
Reload settings: reads the settings again from the server, for example after you changed them on the website. Alt R.

The Codex choices apply to new tasks. A task that is already running keeps the choices it started with until it finishes.

Below these settings there is a second part for local projects, which is saved only on this computer and takes effect straight away, without Save settings. Section 4 explains what it is for.

When a task finishes, update the local projects: when this is ticked, the app updates every local project after each task. It is ticked at the start. Alt W.
Local projects: the folders on this computer that the app keeps up to date. Alt J.
Add folder: asks for the folder where you cloned a repository, and adds it to the list. The app refuses folders that are not Git repositories. Alt A.
Remove folder: removes the selected folder from the list. The folder itself and its files stay on your computer. Alt V.
Update now: updates every local project straight away, even if the box above is not ticked. Alt O.

## 4. Getting Codex changes on your computer

When Codex works on one of your GitHub repositories, it sends its changes to GitHub, not to your computer. You do not have to clone the repository again to get them, because the app can bring them into the folder you already have.

### 4.1 Setting it up once

1. Clone the repository on your computer once, the normal way, for example with `git clone https://github.com/yourname/myproject.git`. This needs Git for Windows.
2. Open the Settings tab, select Add folder, and choose the folder you cloned, for example `Documents\github\myproject`.
3. Leave When a task finishes, update the local projects ticked.

### 4.2 What happens after a task

When a task finishes, after the end sound, the app runs `git pull` in every local project. If something new arrived, a window tells you what changed, for example "myproject got 2 new changes, 3 files changed, 10 insertions(+). Changes: Fix settings menu; Add volume option." If nothing changed, the app only writes that the project is up to date in the status bar, so it does not interrupt you. If the window is not active, you also get a Windows notification.

The app always updates the branch that is open in your folder, which is normally `main`. Codex is told to work on `main` too, so the changes arrive in the branch you already use.

### 4.3 If a project cannot be updated

The app never mixes your changes with the ones from GitHub. If it cannot add the new changes safely, it leaves the folder exactly as it was and tells you why. I will list the common reasons.

This computer has its own changes that are not on GitHub: you changed and committed files in the folder that Codex also changed. Send your changes to GitHub first with `git push`, or ask me for help.
It is not a Git repository: the folder in the list is not a cloned repository, or the hidden .git folder was deleted.
The folder no longer exists: the folder was moved or deleted. Remove it from the list and add it again from its new place.
Git is not installed: install Git for Windows, then select Update now.

If Git asks for your GitHub password, the update stops instead of waiting. This only happens with private repositories that were never opened on this computer, so run `git pull` once yourself in that folder and sign in when Git asks.

## 5. Unpairing and lost computers

If you stop using a computer, open the File menu and select Unpair this computer. The app tells the server to forget it and deletes the saved pairing, so you would need a new code to use it again.

If you lose a computer, or think someone else has used it, open the Devices page on the website and select Remove device next to its name. It stops working straight away, even if the app is open. The next time that app tries to reach the server, it says that it is no longer paired and asks for a new code.

## 6. Things to know

Anyone who can sign in to your Windows account on a paired computer can use the app, because it does not ask for a password after pairing. If this computer is shared, lock Windows when you leave it, or unpair the app.
The app talks to the server over an encrypted connection and checks the server's certificate, so it only connects to the real Codex server.
The pairing codes are long enough that guessing one is not realistic, and the server also slows down repeated wrong attempts.

## 7. Building the app again

You do not need to build anything on your computer. The app lives in a private repository on GitHub, and GitHub builds it with Nuitka every time the code changes, on a Windows machine of its own.

To get the newest build, open the repository on GitHub, then open the Actions tab and select the latest Build run that has a green tick. At the bottom of that page, in the Artifacts section, select CodexDesktop to download a zip with the exe, this guide and the GitHub guide. Artifacts are kept for 90 days. Alternatively, if you want a fresh build without changing the code, open the Build workflow in the Actions tab and select Run workflow.
