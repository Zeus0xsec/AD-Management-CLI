import base64
import getpass
import json
import os
import re
import subprocess

# ====================== WYGLĄD / KOLORY ======================

WIDTH = 60


def _enable_ansi():
    if os.name != "nt":
        return True
    try:
        import ctypes
        kernel32 = ctypes.windll.kernel32
        handle = kernel32.GetStdHandle(-11)
        mode = ctypes.c_ulong()
        if not kernel32.GetConsoleMode(handle, ctypes.byref(mode)):
            return False
        return bool(kernel32.SetConsoleMode(handle, mode.value | 0x0004))
    except Exception:
        return False


USE_COLOR = _enable_ansi()


def paint(text, code):
    return f"\033[{code}m{text}\033[0m" if USE_COLOR else text


def ok(msg):
    print(paint(f"[ OK ] {msg}", "92"))


def err(msg):
    print(paint(f"[BŁĄD] {msg}", "91"))


def warn(msg):
    print(paint(f"[ !  ] {msg}", "93"))


def header(title):
    print()
    print(paint("=" * WIDTH, "96"))
    print(paint(title.center(WIDTH), "1;96"))
    print(paint("=" * WIDTH, "96"))


def clear():
    os.system("cls" if os.name == "nt" else "clear")


def pause():
    input(paint("\nNaciśnij Enter, aby wrócić do menu...", "90"))


def ask(prompt):
    return input(paint(f"  {prompt}: ", "97")).strip()


def ask_yes_no(question):
    answer = input(paint(f"  {question} [t/N]: ", "97")).strip().lower()
    return answer in ("t", "tak", "y", "yes")


# ====================== POWERSHELL ======================

def run_ps(command):
    full_command = (
        "$ErrorActionPreference = 'Stop';"
        "[Console]::OutputEncoding = [System.Text.Encoding]::UTF8;"
        + command
    )
    result = subprocess.run(
        ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", full_command],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if result.returncode == 0:
        return True, result.stdout.strip()
    return False, (result.stderr.strip() or result.stdout.strip())


def ps_quote(value):
    for quote in ("'", "\u2018", "\u2019", "\u201a", "\u201b"): 
        value = value.replace(quote, quote * 2)
    return f"'{value}'"


def show_error(message, details):
    err(message)
    for line in details.splitlines():
        print(paint(f"       {line}", "90"))


# ====================== POMOCNICZE: OU ======================

def ou_label(dn):
    parts = re.split(r"(?<!\\),", dn) 
    names = [p[3:].replace("\\,", ",") for p in parts if p.upper().startswith("OU=")]
    return " / ".join(reversed(names)) or dn


def get_ous():
    cmd = (
        "Get-ADOrganizationalUnit -Filter * | "
        "Select-Object Name, DistinguishedName | ConvertTo-Json -Compress"
    )
    success, out = run_ps(cmd)

    if not success:
        show_error("Nie udało się pobrać listy jednostek OU.", out)
        warn("Upewnij się, że uruchamiasz skrypt na kontrolerze domeny z modułem ActiveDirectory.")
        return None
    if not out:
        return []

    try:
        ous = json.loads(out)
    except json.JSONDecodeError:
        show_error("Nie udało się odczytać odpowiedzi z PowerShella.", out)
        return None

    if isinstance(ous, dict): 
        ous = [ous]
    ous.sort(key=lambda o: ou_label(o.get("DistinguishedName") or "").lower())
    return ous


def pick_ou(ous, zero_label):
    print()
    print(paint("  Dostępne jednostki OU:", "1"))
    print(f"  {paint('[0]', '96')} {zero_label}")
    for index, ou in enumerate(ous, 1):
        tag = paint(f"[{index}]", "96")
        print(f"  {tag} {ou_label(ou['DistinguishedName'])}")
        print(paint(f"        {ou['DistinguishedName']}", "90"))
    print()

    choice = ask(f"Wybierz numer (0-{len(ous)})")
    if not choice.isdigit() or int(choice) > len(ous):
        err(f"Niepoprawny wybór. Wpisz liczbę od 0 do {len(ous)}.")
        return False, None

    number = int(choice)
    return True, (None if number == 0 else ous[number - 1]["DistinguishedName"])


# ====================== FUNKCJE ======================

def list_users():
    header("LISTA UŻYTKOWNIKÓW ACTIVE DIRECTORY")
    cmd = (
        "Get-ADUser -Filter * -Properties Title | "
        "Select-Object SamAccountName, Name, Enabled, Title | ConvertTo-Json -Compress"
    )
    success, out = run_ps(cmd)

    if not success:
        show_error("Nie udało się pobrać listy użytkowników.", out)
        warn("Upewnij się, że uruchamiasz skrypt na kontrolerze domeny z modułem ActiveDirectory.")
        return
    if not out:
        warn("Brak użytkowników do wyświetlenia.")
        return

    try:
        users = json.loads(out)
    except json.JSONDecodeError:
        show_error("Nie udało się odczytać odpowiedzi z PowerShella.", out)
        return

    if isinstance(users, dict): 
        users = [users]
    users.sort(key=lambda u: (u.get("SamAccountName") or "").lower())

    rows = [
        (
            u.get("SamAccountName") or "",
            u.get("Name") or "",
            "Aktywne" if u.get("Enabled") else "Zablokowane",
            u.get("Title") or "-",
        )
        for u in users
    ]
    heads = ("Login", "Imię i nazwisko", "Status", "Stanowisko")
    widths = [max(len(h), *(len(r[i]) for r in rows)) for i, h in enumerate(heads)]

    head_line = "  ".join(h.ljust(w) for h, w in zip(heads, widths))
    print()
    print(paint(head_line, "1"))
    print("-" * len(head_line))
    for login, name, status, title in rows:
        status_cell = paint(status.ljust(widths[2]), "92" if status == "Aktywne" else "91")
        print(f"{login.ljust(widths[0])}  {name.ljust(widths[1])}  {status_cell}  {title}")
    print(f"\nŁącznie użytkowników: {len(rows)}")


def add_user():
    header("DODAWANIE NOWEGO UŻYTKOWNIKA")

    ous = get_ous()
    if ous is None:
        if not ask_yes_no("Kontynuować i utworzyć użytkownika w domyślnym kontenerze Users?"):
            return
        ous = []

    ou_dn = None
    if ous:
        valid, ou_dn = pick_ou(ous, "Domyślny kontener Users (bez wyboru OU)")
        if not valid:
            return
    else:
        warn("Brak dostępnych OU - użytkownik trafi do domyślnego kontenera Users.")

    print()
    username = ask("Login (SamAccountName) [np. jkowalski]")
    firstname = ask("Imię")
    lastname = ask("Nazwisko")

    if not username or not firstname or not lastname:
        err("Wszystkie pola muszą być wypełnione.")
        return

    fullname = f"{firstname} {lastname}"
    cmd = (
        f"New-ADUser -SamAccountName {ps_quote(username)} "
        f"-GivenName {ps_quote(firstname)} -Surname {ps_quote(lastname)} "
        f"-Name {ps_quote(fullname)} -Enabled $true"
    )
    if ou_dn:
        cmd += f" -Path {ps_quote(ou_dn)}"
    success, out = run_ps(cmd)

    if success:
        location = ou_label(ou_dn) if ou_dn else "Users"
        ok(f"Użytkownik {fullname} ({username}) został utworzony w AD! Lokalizacja: {location}")
    else:
        show_error("Nie udało się utworzyć użytkownika.", out)


def reset_password():
    header("RESETOWANIE HASŁA UŻYTKOWNIKA")
    username = ask("Login użytkownika (SamAccountName)")
    if not username:
        err("Login nie może być pusty.")
        return

    new_password = getpass.getpass("  Nowe hasło (niewidoczne): ")
    repeat_password = getpass.getpass("  Powtórz nowe hasło: ")

    if not new_password:
        err("Hasło nie może być puste.")
        return
    if new_password != repeat_password:
        err("Hasła nie są identyczne.")
        return

    base64_password = base64.b64encode(new_password.encode("utf-16le")).decode("utf-8")

    cmd = (
        f"$Bstr = [System.Convert]::FromBase64String('{base64_password}');"
        "$SecPass = [System.Text.Encoding]::Unicode.GetString($Bstr) | ConvertTo-SecureString -AsPlainText -Force;"
        f"Set-ADAccountPassword -Identity {ps_quote(username)} -NewPassword $SecPass -Reset"
    )
    success, out = run_ps(cmd)

    if not success:
        show_error("Nie udało się zresetować hasła.", out)
        return

    ok(f"Hasło użytkownika '{username}' zostało zresetowane!")

    if ask_yes_no("Wymusić zmianę hasła przy następnym logowaniu?"):
        success, out = run_ps(f"Set-ADUser -Identity {ps_quote(username)} -ChangePasswordAtLogon $true")
        if success:
            ok("Użytkownik będzie musiał zmienić hasło przy logowaniu.")
        else:
            show_error("Nie udało się ustawić wymuszenia zmiany hasła.", out)


def toggle_user():
    header("BLOKOWANIE / ODBLOKOWANIE KONTA")
    username = ask("Login użytkownika (SamAccountName)")

    print()
    print("  [1] Zablokuj konto (Disable)")
    print("  [2] Odblokuj konto (Enable)")
    action = ask("Wybierz akcję (1 lub 2)")

    if not username or action not in ("1", "2"):
        err("Niepoprawny login lub wybór akcji.")
        return

    if action == "1":
        cmd = f"Disable-ADAccount -Identity {ps_quote(username)}"
        status_text = "zablokowane"
    else:
        cmd = f"Enable-ADAccount -Identity {ps_quote(username)}"
        status_text = "odblokowane"

    success, out = run_ps(cmd)

    if success:
        ok(f"Konto '{username}' zostało {status_text}!")
    else:
        show_error("Nie udało się zmienić statusu konta.", out)


def delete_user():
    header("USUWANIE UŻYTKOWNIKA")
    username = ask("Login użytkownika do usunięcia (SamAccountName)")

    if not username:
        err("Login nie może być pusty.")
        return

    warn(f"Konto '{username}' zostanie usunięte bezpowrotnie!")
    confirm = ask("Wpisz TAK, aby potwierdzić")
    if confirm != "TAK":
        warn("Anulowano usuwanie użytkownika.")
        return

    success, out = run_ps(f"Remove-ADUser -Identity {ps_quote(username)} -Confirm:$false")

    if success:
        ok(f"Użytkownik '{username}' został usunięty z Active Directory!")
    else:
        show_error("Nie udało się usunąć użytkownika.", out)


def create_ou():
    header("TWORZENIE ORGANIZATIONAL UNIT (OU)")
    ou_name = ask("Nazwa nowej OU [np. Sprzedaz]")

    if not ou_name:
        err("Nazwa OU nie może być pusta.")
        return
    if re.search(r'[,\\=+"<>;#]', ou_name):
        err('Nazwa OU nie może zawierać znaków: , \\ = + " < > ; #')
        return

    ous = get_ous()
    if ous is None:
        if not ask_yes_no("Kontynuować i utworzyć OU w głównym katalogu domeny?"):
            return
        ous = []

    parent_dn = None
    if ous:
        valid, parent_dn = pick_ou(ous, "Główny katalog domeny (bez rodzica)")
        if not valid:
            return
    else:
        warn("Brak istniejących OU - nowa OU zostanie utworzona w głównym katalogu domeny.")

    cmd = f"New-ADOrganizationalUnit -Name {ps_quote(ou_name)}"
    if parent_dn:
        cmd += f" -Path {ps_quote(parent_dn)}"
    success, out = run_ps(cmd)

    if success:
        location = ou_label(parent_dn) if parent_dn else "główny katalog domeny"
        ok(f"Jednostka OU '{ou_name}' została utworzona! Lokalizacja: {location}")
    else:
        show_error("Nie udało się utworzyć jednostki OU.", out)


def delete_ou():
    header("USUWANIE ORGANIZATIONAL UNIT (OU)")

    ous = get_ous()
    if ous is None:
        return
    if not ous:
        warn("Brak jednostek OU do usunięcia.")
        return

    valid, ou_dn = pick_ou(ous, "Anuluj (nie usuwaj niczego)")
    if not valid:
        return
    if ou_dn is None:
        warn("Anulowano usuwanie OU.")
        return

    children = [
        o["DistinguishedName"] for o in ous
        if o["DistinguishedName"].lower().endswith("," + ou_dn.lower())
    ]

    print()
    warn(f"OU '{ou_label(ou_dn)}' zostanie usunięta bezpowrotnie razem z CAŁĄ zawartością:")
    warn("użytkownikami, komputerami, grupami i podrzędnymi jednostkami OU!")
    if children:
        warn(f"Liczba podrzędnych jednostek OU: {len(children)}")
    if ask("Wpisz TAK, aby potwierdzić") != "TAK":
        warn("Anulowano usuwanie OU.")
        return


    if children:
        unprotect = "; ".join(
            f"Set-ADOrganizationalUnit -Identity {ps_quote(child)} -ProtectedFromAccidentalDeletion $false"
            for child in children
        )
        success, out = run_ps(unprotect)
        if not success:
            show_error("Nie udało się zdjąć ochrony z podrzędnych jednostek OU.", out)
            return

    cmd = (
        f"Set-ADOrganizationalUnit -Identity {ps_quote(ou_dn)} -ProtectedFromAccidentalDeletion $false; "
        f"Remove-ADOrganizationalUnit -Identity {ps_quote(ou_dn)} -Recursive -Confirm:$false"
    )
    success, out = run_ps(cmd)

    if success:
        ok(f"Jednostka OU '{ou_label(ou_dn)}' została usunięta z Active Directory!")
    else:
        show_error("Nie udało się usunąć jednostki OU.", out)


# ====================== MENU ======================

def show_menu():
    actions = {
        "1": list_users,
        "2": add_user,
        "3": reset_password,
        "4": toggle_user,
        "5": delete_user,
        "6": create_ou,
        "7": delete_ou,
    }

    while True:
        clear()
        header("ACTIVE DIRECTORY MANAGEMENT CLI")
        print()
        print(f"  {paint('[1]', '96')} Wyświetl użytkowników AD")
        print(f"  {paint('[2]', '96')} Dodaj nowego użytkownika")
        print(f"  {paint('[3]', '96')} Resetuj hasło użytkownika")
        print(f"  {paint('[4]', '96')} Zablokuj / Odblokuj konto")
        print(f"  {paint('[5]', '96')} Usuń użytkownika")
        print(f"  {paint('[6]', '96')} Utwórz Organizational Unit (OU)")
        print(f"  {paint('[7]', '96')} Usuń Organizational Unit (OU)")
        print(f"  {paint('[0]', '91')} Wyjście")
        print()

        choice = ask("Wybierz opcję (0-7)")

        if choice == "0":
            print("\nZamykanie programu...")
            break
        elif choice in actions:
            actions[choice]()
            pause()
        else:
            warn("Niepoprawny wybór. Wpisz cyfrę od 0 do 7.")
            pause()


def check_ad_module():
    success, out = run_ps("Import-Module ActiveDirectory")
    if not success:
        warn("Nie można załadować modułu ActiveDirectory - większość funkcji nie zadziała.")
        warn("Uruchom skrypt na kontrolerze domeny lub zainstaluj RSAT.")
        pause()


if __name__ == "__main__":
    try:
        check_ad_module()
        show_menu()
    except KeyboardInterrupt:
        print("\n\nPrzerwano. Zamykanie programu...")
