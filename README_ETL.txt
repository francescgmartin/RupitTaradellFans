# ETL Rupit-Taradell

## Com usar-ho
1. Col·loca els fitxers CSV a la carpeta `data/`.
2. Els YAML de mapping són a `configs/`.
3. Executa:
   ```bash
   python3 etl.py
   ```
4. Sortida: JSON per any a la carpeta `out/`.

## Camps sortida
- bib
- full_name
- first_name
- last_name
- gender
- club
- status
- time_net (segons)
- sant_julia (segons)
- runner_id (hash SHA1)

## Info edició
Inclou any, nom, distància i desnivell.
