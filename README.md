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

The main window has five tabs. Press Control Tab to move between them. Every field and list has a shortcut, shown as an underlined letter, so Alt and that letter jumps straight to it.

### 3.1 Tasks

This tab is where you talk to Codex. It contains the following.

Task for Codex: the box where you write what Codex should do. Alt T jumps here.
Submit task: sends the task. Alt S. While a task runs, this button is unavailable, because Codex works on one task at a time.
Stop task: stops the task that is running. Alt O.
Codex answer: the answer, which grows as Codex works. Alt A jumps here, and you can read it with the arrow keys like any text.
Previous tasks: the last 20 tasks. Select one and press Enter to show its answer in the Codex answer box. Alt P.
Refresh previous tasks: reloads the list. Alt R.

When a task finishes, the app plays a sound and shows the result in the status bar. If the window is not active, it also shows a Windows notification, so you can do something else while Codex works. If you close the app while a task runs, the task keeps running on the server, and the app follows it again the next time you open it.

The answer box does not read new text aloud by itself, because Windows boxes do not announce text added to them. Instead, wait for the sound at the end, or move to the box and read what is there so far.

### 3.2 Files

This tab shows the files in the working folder on the server, with their sizes, and has these buttons.

Refresh: reloads the list.
Download file: downloads the selected file to a place you choose.
Download folder of the selected file: downloads the folder that contains the selected file, as a zip file. The app shows the folder path first, so you can shorten it to download a bigger folder.
Download everything: downloads the whole working folder as a zip file.
Upload file: sends one file of up to 2 GB. If it is a zip or tar archive, the server extracts it into a new folder, the same as the website does.
Upload folder: sends a whole folder from your computer, with all its subfolders, into a folder with the same name on the server. Files that already exist there are replaced, so you can send an updated version of a project the same way. Archives inside the folder are not extracted, so your project stays exactly as it is. The folders `__pycache__`, `node_modules`, `.venv`, `venv`, `.mypy_cache` and `.pytest_cache` are skipped, because they are large and can be rebuilt.

Uploads and downloads show a progress window, which you can cancel.

### 3.3 Repositories

This tab manages the GitHub keys, the same as the Repositories page on the website. The GitHub guide in GITHUB.md explains how they work and how to give Codex tasks for your projects.

Add repository: asks for a short name and the GitHub repository, then shows the public key and the address for Codex, with buttons to copy them and to open the right GitHub page.
Show key and address: shows the same window again for the selected repository.
Remove key: deletes the key of the selected repository from the server, then offers to open the GitHub page so you can delete it there too.

### 3.4 Log

This tab shows the same log as the website, newest first, with sign-ins, tasks, uploads and device changes. Select Refresh to reload it.

### 3.5 Settings

This tab has the same setting as the Settings page on the website, and changing it in one place changes it in the other.

Show technical details in Codex answers: when this is ticked, the answer also shows the session number, the commands Codex runs with their output, and the number of tokens used. When it is not ticked, you only see what Codex writes to you, and errors. Alt D jumps here.
Save settings: saves the choice on the server. Alt S. A task that is already running keeps the old setting until it finishes.

## 4. Unpairing and lost computers

If you stop using a computer, open the File menu and select Unpair this computer. The app tells the server to forget it and deletes the saved pairing, so you would need a new code to use it again.

If you lose a computer, or think someone else has used it, open the Devices page on the website and select Remove device next to its name. It stops working straight away, even if the app is open. The next time that app tries to reach the server, it says that it is no longer paired and asks for a new code.

## 5. Things to know

Anyone who can sign in to your Windows account on a paired computer can use the app, because it does not ask for a password after pairing. If this computer is shared, lock Windows when you leave it, or unpair the app.
The app talks to the server over an encrypted connection and checks the server's certificate, so it only connects to the real Codex server.
The pairing codes are long enough that guessing one is not realistic, and the server also slows down repeated wrong attempts.

## 6. Building the app again

You do not need to build anything on your computer. The app lives in a private repository on GitHub, and GitHub builds it with Nuitka every time the code changes, on a Windows machine of its own.

To get the newest build, open the repository on GitHub, then open the Actions tab and select the latest Build run that has a green tick. At the bottom of that page, in the Artifacts section, select CodexDesktop to download a zip with the exe, this guide and the GitHub guide. Artifacts are kept for 90 days. Alternatively, if you want a fresh build without changing the code, open the Build workflow in the Actions tab and select Run workflow.
