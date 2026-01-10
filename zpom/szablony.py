# Plik: szablony.py

# Słownik przechowujący wszystkie Twoje wzory
BIBLIOTEKA_SZABLONOW = {
    
    "Wezwanie do zapłaty": """
Miejscowość: {{ miasto }}, Data: {{ data_biezaca }}

NADAWCA:
{{ wierzyciel_nazwa }}
NIP: {{ wierzyciel_nip }}

ODBIORCA:
{{ dluznik_nazwa }}
{{ dluznik_adres }}

WEZWANIE DO ZAPŁATY

W związku z nieuregulowaniem płatności za fakturę nr {{ nr_faktury }} 
z dnia {{ data_faktury }} na kwotę {{ kwota_brutto }}, 
wzywamy do natychmiastowej zapłaty należności.

Prosimy o wpłatę na konto:
{{ nr_konta }} ({{ nazwa_banku }})

W przypadku braku wpłaty w ciągu 7 dni sprawa zostanie skierowana na drogę sądową.

Z poważaniem,
{{ wierzyciel_nazwa }}
""",

    "Podziękowanie za współpracę": """
Miejscowość: {{ miasto }}, Data: {{ data_biezaca }}

Szanowni Państwo,
Firma {{ dluznik_nazwa }} 

Chcielibyśmy serdecznie podziękować za terminowe uregulowanie 
faktury nr {{ nr_faktury }}.

Cieszymy się z naszej współpracy i liczymy na dalsze owocne kontakty biznesowe.

Z wyrazami szacunku,
Zespół {{ wierzyciel_nazwa }}
""",

    "Nota korygująca (Uproszczona)": """
Miejscowość: {{ miasto }}, Data: {{ data_biezaca }}

NOTA KORYGUJĄCA
do faktury VAT nr {{ nr_faktury }} z dnia {{ data_faktury }}

SPRZEDAWCA: {{ wierzyciel_nazwa }}, NIP: {{ wierzyciel_nip }}
NABYWCA: {{ dluznik_nazwa }}

TREŚĆ KOREKTY:
Błędny zapis: _________________________
Prawidłowy zapis: _________________________

Prosimy o akceptację noty.

Podpis wystawcy: ........................
"""
}    