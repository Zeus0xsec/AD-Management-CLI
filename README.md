<img width="955" height="508" alt="3" src="https://github.com/user-attachments/assets/c6b9cc43-3bad-4885-8c11-69e809dacad5" />

# Active Directory Management CLI (`ad_manager`)

A lightweight Python command-line interface (CLI) tool designed to automate local Active Directory administration on Windows Server 2025 and simulate identity-based operations within a hybrid SOC lab environment.

## Features

The interactive terminal menu supports core domain administration tasks:
* **[1] List AD Users** (`Wyświetl użytkowników AD`) – quick enumeration of domain user accounts.
* **[2] Add New User** (`Dodaj nowego użytkownika`) – automated creation of new domain user objects.
* **[3] Reset User Password** (`Resetuj hasło użytkownika`) – secure password resets supporting special characters via Base64 encoding.
* **[4] Enable / Disable Account** (`Zablokuj / Odblokuj konto`) – rapid access control management and incident containment.
* **[5] Delete User** (`Usuń użytkownika`) – removal of user accounts from the domain.
* **[6] Create Organizational Unit (OU)** (`Utwórz Organizational Unit (OU)`) – creation of AD OU containers.
* **[7] Delete Organizational Unit (OU)** (`Usuń Organizational Unit (OU)`) – removal of AD OU containers.

## Technical Highlights
* **Native Windows ANSI Support:** Color-coded status output (`[ OK ]`, `[BŁĄD]`, `[ ! ]`) enabled dynamically via `ctypes` and the Windows API (`kernel32`).
* **PowerShell Integration:** Executes `ActiveDirectory` module cmdlets directly from Python using `subprocess` and Base64 payload encoding.
* **Standalone Packaging:** Designed to be compiled into a portable `ad_manager.exe` binary using `PyInstaller`.
* **Localization Note:** *The interactive CLI prompts and status messages in the current release are localized in Polish.*

## Hybrid SOC Lab Use Case (Red Team / Blue Team)

This tool is actively used as part of a hybrid detection engineering lab built on **Windows Server 2025** (`DC01.cyberlab.local`), **Azure Arc**, and **Microsoft Sentinel / Defender**:
1. **Attack Simulation (Red Team):** Generating realistic administrative and privilege escalation telemetry in Active Directory.
2. **Local Auditing:** Verifying Windows Security Event Logs in Event Viewer (specifically Event IDs `4728`, `4732`, `4737`, and `4662`).
3. **Cloud Detection (Blue Team):** Validating custom KQL analytics rules in Microsoft Sentinel mapped to **MITRE ATT&CK T1098 (Account Manipulation)** under the *Persistence* and *Privilege Escalation* tactics.

## Requirements & Usage

* Windows Server with the **AD DS** role and the `ActiveDirectory` PowerShell module installed.
* Python 3.x executed inside an elevated (**Administrator**) terminal:

```bash
python ad_manager.py
