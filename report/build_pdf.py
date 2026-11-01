"""
Imprime report/rapport.html en report/rapport.pdf avec Chrome (ou Edge) en mode headless.
Les polices viennent de Google Fonts : il faut une connexion internet.
Si rapport.pdf est ouvert dans un lecteur, la nouvelle version va dans rapport_nouveau.pdf.

    python report/build_pdf.py
"""

import pathlib
import shutil
import subprocess
import tempfile

DOSSIER = pathlib.Path(__file__).resolve().parent
NAVIGATEURS = [
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
]

if __name__ == "__main__":
    navigateur = next(p for p in NAVIGATEURS if pathlib.Path(p).exists())
    brouillon = pathlib.Path(tempfile.gettempdir()) / "rapport_lattice.pdf"
    subprocess.run([navigateur, "--headless=new", "--disable-gpu", "--no-pdf-header-footer",
                    "--virtual-time-budget=15000", f"--print-to-pdf={brouillon}",
                    (DOSSIER / "rapport.html").as_uri()], check=True, capture_output=True)
    for nom in ("rapport.pdf", "rapport_nouveau.pdf"):
        try:
            shutil.copyfile(brouillon, DOSSIER / nom)
            print("PDF ecrit :", DOSSIER / nom)
            break
        except PermissionError:
            print(nom, "est ouvert ailleurs, on essaie le nom suivant")
    else:
        print("aucun nom libre : le PDF est dans", brouillon)
