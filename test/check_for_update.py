import sys
import requests
from PyQt6.QtWidgets import QApplication, QMessageBox

def check_for_update():
    # GitHub Pages URL where your update_info.json is hosted
    update_info_url = "https://m-kareem.github.io/yorku-phys-lab-seating/update_info.json"

    try:
        # Fetch update information from the GitHub Pages URL
        response = requests.get(update_info_url)
        update_info = response.json()

        # Extract version information from the JSON response
        latest_version = update_info.get('version')

        # Compare latest version with your installed version
        installed_version = "1.0.0"  # Replace this with your actual installed version
        if latest_version != installed_version:
            # Alert the user about the update
            reply = QMessageBox.question(
                None,
                "Update Available",
                f"A new version ({latest_version}) is available. Do you want to update?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )

            if reply == QMessageBox.StandardButton.Yes:
                # Open the download URL in a browser to prompt the user for download
                download_url = update_info.get('download_url')
                if download_url:
                    import webbrowser
                    webbrowser.open(download_url)
        else:
            QMessageBox.information(None, "No Updates", "You have the latest version.")

    except Exception as e:
        print(f"Error fetching update information: {e}")
        QMessageBox.critical(None, "Error", "Failed to check for updates.")

# Usage example:
if __name__ == "__main__":
    app = QApplication(sys.argv)
    check_for_update()
    sys.exit(app.exec())
