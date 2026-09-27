# Dílčí úkol: Marže plodin v roce 2024

Skript můžeš poslat samostatně. Ke spuštění potřebuje tři datové soubory: hledá je nejdřív vedle sebe a potom v aktuální pracovní složce. Výsledek uloží do složky, ve které vstupy našel. Pokud posíláš celý adresář `Odevzdání`, už obsahuje skript, vstupy i připravenou výslednou tabulku.

Požadavky: Python 3.9 nebo novější.

Závislosti nainstaluj příkazem:

```powershell
python -m pip install -r requirements.txt
```

Potom spusť skript; jeho jediným výstupem je `marze_2024.csv` se sloupci `Plodina` a `Marze_Mi_Kc_ha`. Při úspěšném běhu nic nevypisuje.

```powershell
python vypocet_marzi_2024.py
```

Závislosti jsou omezené na pandas a openpyxl a jsou uvedené v `requirements.txt`.
