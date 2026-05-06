Name:           kerio-rpm
Version:        0.1.0
Release:        1%{?dist}
Summary:        Kerio VPN Manager GUI

License:        MIT
URL:            https://github.com/vgeroutskis/kerio-rpm
Source0:        %{name}-%{version}.tar.gz

BuildArch:      noarch
BuildRequires:  python3-devel
Requires:       python3
Requires:       python3-gobject
Requires:       libadwaita
Requires:       libayatana-appindicator-gtk3
Requires:       podman

%description
A GTK4/Libadwaita GUI to manage Kerio VPN via Podman.

%prep
%autosetup

%install
install -d %{buildroot}%{_bindir}
install -d %{buildroot}%{_datadir}/%{name}
install -d %{buildroot}%{_datadir}/applications

# Install source files
cp -r src/* %{buildroot}%{_datadir}/%{name}/

# Install docker-compose.yml
install -m 0644 docker-compose.yml %{buildroot}%{_datadir}/%{name}/docker-compose.yml

# Create wrapper script with error handling
cat > %{buildroot}%{_bindir}/%{name} <<WEOF
#!/bin/bash
# Wrapper for %{name}
set -e

if [[ ! -f "%{_datadir}/%{name}/main.py" ]]; then
    echo "Error: Required file %{_datadir}/%{name}/main.py not found." >&2
    exit 1
fi

exec python3 %{_datadir}/%{name}/main.py "\$@"
WEOF
chmod +x %{buildroot}%{_bindir}/%{name}

# Create desktop entry
cat > %{buildroot}%{_datadir}/applications/%{name}.desktop <<DEOF
[Desktop Entry]
Name=Kerio VPN
Comment=Manage Kerio VPN
Exec=%{name}
Icon=network-vpn-symbolic
Terminal=false
Type=Application
Categories=Network;
StartupNotify=true
DEOF

%check
%{python3} src/test_config.py

%files
%{_bindir}/%{name}
%{_datadir}/%{name}/
%{_datadir}/applications/%{name}.desktop

%changelog
* Wed May 06 2026 vgeroutskis <vgeroutskis@example.com> - 0.1.0-1
- Initial release
