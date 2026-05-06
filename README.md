# Kerio RPM

A modern GTK4/Libadwaita GUI manager for Kerio Control VPN on Fedora Linux. It simplifies VPN management by providing a native interface for configuration and connection control, using Podman as a backend.

## Features

- **Native UI**: Built with GTK4 and Libadwaita for a seamless Fedora integration.
- **Easy Configuration**: User-friendly form to set up server, username, and password.
- **Auto-Detect Fingerprint**: Automatically fetches the server's SSL fingerprint.
- **System Tray**: Unobtrusive tray icon for quick status checks and control.
- **Rootless**: Runs via Podman in user space (no root required for daily use).
- **Automated Packaging**: Built-in RPM spec and GitHub Actions for easy distribution.

## Installation

### Prerequisites

- Fedora Linux (39 or newer recommended)
- Podman installed (`sudo dnf install podman`)

### Installing the RPM

Download the latest `.rpm` from the [Releases](https://github.com/VGeroutskis/kerio-rpm/releases) page and install it:

```bash
sudo dnf install ./kerio-rpm-*.rpm
```

## Usage

1. Launch **Kerio VPN** from your application menu.
2. On first run, the **Settings** window will appear.
3. Enter your VPN server, username, and password.
4. Click **Fetch Fingerprint** to automatically get the server's identity.
5. Click **Save**. The app will automatically set up the required Podman container.
6. Use the main switch to **Connect** or **Disconnect**.

## Development

To run the application from source:

```bash
# Clone the repository
git clone https://github.com/VGeroutskis/kerio-rpm.git
cd kerio-rpm

# Run the app
python3 src/main.py
```

## License

MIT License
