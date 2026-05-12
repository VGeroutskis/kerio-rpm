Name:           kerio-rpm
Version:        1.1.1
Release:        1%{?dist}
Summary:        Modern GTK4 GUI for Kerio Control VPN (Podman based)

License:        MIT
URL:            https://github.com/cognitera/kerio-rpm
Source0:        %{name}-%{version}.tar.gz

BuildArch:      noarch
Requires:       python3
Requires:       python3-gobject
Requires:       gtk4
Requires:       libadwaita
Requires:       podman
Requires:       podman-compose
Requires:       polkit
Requires:       openssl
Requires:       bind-utils
Requires:       libappindicator-gtk3
Requires:       python3-gobject-base

%description
A modern Linux GUI for Kerio Control VPN that uses a rootless Podman 
container as the backend. Features split-tunneling management and XOR password encryption.

%prep
%setup -q

%build
# No compilation needed for Python

%install
mkdir -p %{buildroot}%{_bindir}
mkdir -p %{buildroot}%{_datadir}/%{name}
mkdir -p %{buildroot}%{_datadir}/%{name}/src
mkdir -p %{buildroot}%{_datadir}/applications
mkdir -p %{buildroot}%{_datadir}/polkit-1/actions
mkdir -p %{buildroot}%{_datadir}/polkit-1/rules.d

# Copy source files
cp src/*.py %{buildroot}%{_datadir}/%{name}/src/
cp src/*.sh %{buildroot}%{_datadir}/%{name}/src/
chmod +x %{buildroot}%{_datadir}/%{name}/src/vpn-helper.sh
cp docker-compose.yml %{buildroot}%{_datadir}/%{name}/

# Desktop file
if [ -f data/com.cognitera.kerio-rpm.desktop ]; then
    cp data/com.cognitera.kerio-rpm.desktop %{buildroot}%{_datadir}/applications/
else
    cat > %{buildroot}%{_datadir}/applications/com.cognitera.kerio-rpm.desktop <<EOD
[Desktop Entry]
Name=Kerio VPN
Comment=Manage Kerio Control VPN connection
Exec=kerio-rpm
Icon=network-vpn-symbolic
Terminal=false
Type=Application
Categories=Network;VPN;
StartupNotify=true
EOD
fi

# Polkit files
cp data/com.cognitera.kerio-rpm.policy %{buildroot}%{_datadir}/polkit-1/actions/
mkdir -p %{buildroot}%{_sysconfdir}/polkit-1/rules.d
cp data/10-kerio-rpm.rules %{buildroot}%{_sysconfdir}/polkit-1/rules.d/

# Launcher script
cat > %{buildroot}%{_bindir}/kerio-rpm <<EOD
#!/bin/bash
export PYTHONPATH=%{_datadir}/%{name}/src
exec /usr/bin/python3 %{_datadir}/%{name}/src/main.py "$@"
EOD
chmod +x %{buildroot}%{_bindir}/kerio-rpm

%files
%{_bindir}/%{name}
%{_datadir}/%{name}/
%{_datadir}/applications/*.desktop
%{_datadir}/polkit-1/actions/*.policy
%{_sysconfdir}/polkit-1/rules.d/*.rules

%changelog
* Fri May 08 2026 Valentinos Geroutskis <vgeroutskis@example.com> - 1.0.0-1
- Initial release with split-tunneling and GTK4 UI
