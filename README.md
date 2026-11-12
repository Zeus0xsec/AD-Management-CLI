<img width="955" height="508" alt="3" src="https://github.com/user-attachments/assets/c6b9cc43-3bad-4885-8c11-69e809dacad5" />

# Active Directory Management CLI (`ad_manager`)

Narzędzie wiersza poleceń (CLI) napisane w Pythonie do automatyzacji zarządzania obiektami w lokalnym Active Directory (Windows Server 2025) oraz przeprowadzania kontrolowanych symulacji w hybrydowym laboratorium SOC.

## Funkcjonalności

Interaktywne menu terminala obsługuje kluczowe operacje administracyjne na domenie:
* **[1] Wyświetl użytkowników AD** – szybki podgląd kont domenowych.
* **[2] Dodaj nowego użytkownika** – tworzenie nowych obiektów użytkowników w AD.
* **[3] Resetuj hasło użytkownika** – bezpieczna zmiana hasła z obsługą znaków specjalnych.
* **[4] Zablokuj / Odblokuj konto** – natychmiastowe zarządzanie statusem dostępu konta.
* **[5] Usuń użytkownika** – usuwanie kont z domeny.
* **[6] Utwórz Organizational Unit (OU)** – budowanie struktury jednostek organizacyjnych.
* **[7] Usuń Organizational Unit (OU)** – usuwanie jednostek organizacyjnych.

## Cechy techniczne
* **Interfejs konsolowy:** Kolorowanie komunikatów statusu (`[ OK ]`, `[BŁĄD]`, `[ ! ]`) z natywną obsługą sekwencji ANSI w konsoli Windows (wykorzystanie `ctypes` oraz Windows API).
* **Integracja z PowerShell:** Wykonywanie poleceń modułu `ActiveDirectory` z poziomu Pythona (`subprocess`, kodowanie `base64`).
* **Dystrybucja:** Możliwość spakowania skryptu do samodzielnego pliku wykonywalnego `ad_manager.exe` za pomocą narzędzia `PyInstaller`.

## Zastosowanie w laboratorium SOC (Red Team / Blue Team)

Projekt stanowi element poligonu badawczego opartego na **Windows Server 2025**, **Azure Arc** oraz **Microsoft Sentinel / Defender**:
1. **Symulacja operacji (Red Team):** Generowanie zdarzeń administracyjnych oraz eskalacji uprawnień w domenie.
2. **Audyt lokalny:** Weryfikacja logów bezpieczeństwa w Windows Event Viewer (m.in. Event ID `4728`, `4732`, `4737`, `4662`).
3. **Detekcja w chmurze (Blue Team):** Testowanie niestandardowych reguł analitycznych KQL w Microsoft Sentinel zmapowanych na macierz **MITRE ATT&CK** (m.in. technika **T1098 – Account Manipulation** oraz taktyki *Persistence* i *Privilege Escalation*).

## Wymagania i uruchomienie

* System Windows Server z zainstalowaną rolą AD DS oraz modułem `ActiveDirectory` dla PowerShella.
* Python 3.x (uruchomiony w terminalu z uprawnieniami **Administratora**):

```bash
python ad_manager.py
