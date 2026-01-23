# Qred

Qred - Quote Recurrent Editor & Dump to bot Discord, który pozwala na zbieranie, wyświetlanie i zarządzanie cytatami w Twoim serwerze. Możesz dodawać własne cytaty, wyświetlać losowe, przeglądać według autora oraz otrzymywać codzienny cytat.

## How to use
• Dodaj bota do swojego serwera przy użyciu linku: https://discord.com/oauth2/authorize?client_id=1464359456660914403

• Używaj komend slash, aby dodawać cytaty, przeglądać je według autora, losowo lub codziennie. Aby zobaczyć wszystkie dostępne komendy, wpisz /commands.

## How to run your own instance
Stwórz plik `.env` zawierający:

- Twój Discord ID  
- Token bota Discord  

Zainstaluj wszystkie wymagane pakiety Pythona z `requirements.txt`.

Uruchom bota używając `.vbs` lub bezpośrednio w Pythonie, aby działał w tle.

Aby wyłączyć bota, użyj komendy /shutdown.

## Notes
- Cytaty zapisują się automatycznie z autorem i datą w formacie DD/MM/YYYY.  
- Bot obsługuje mieszankę dużych i małych liter przy autorach.  
- Autorzy dodani przez komendę /createquote są automatycznie zapisywani.  
- Codzienny cytat (/dailyquote) wybierany jest według systemu zapętlania daty.  
