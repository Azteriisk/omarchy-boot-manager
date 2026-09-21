# Maintainer: Azteriisk
pkgname=omarchy-boot-manager-git
pkgver=1.0.0
pkgrel=1
pkgdesc="Windows dual-boot chainloader, sbctl Secure Boot enrollment for anti-cheat games, and reboot controls for Omarchy"
arch=('any')
url="https://github.com/Azteriisk/omarchy-boot-manager"
license=('MIT')
depends=('python' 'python-gobject' 'gtk4' 'libadwaita' 'efibootmgr' 'sbctl')
makedepends=('git')
provides=('omarchy-boot-manager')
conflicts=('omarchy-boot-manager')
_commit="1ec113bdb6c63597c4f3378ac9f1116c3472b717"
source=("${pkgname}::git+https://github.com/Azteriisk/omarchy-boot-manager.git#commit=${_commit}")
sha256sums=('SKIP')

pkgver() {
  cd "$srcdir/${pkgname}"
  git describe --long --tags --abbrev=7 2>/dev/null | sed 's/^v//;s/\([^-]*-g\)/r\1/;s/-/./g' ||
  printf "1.0.0.r%s.%s" "$(git rev-list --count HEAD)" "$(git rev-parse --short=7 HEAD)"
}

package() {
  cd "$srcdir/${pkgname}"
  install -dm755 "$pkgdir/usr/share/omarchy/plugins/azterisk.boot"
  cp -a manifest.json Service.qml scripts omarchy-boot.desktop README.md "$pkgdir/usr/share/omarchy/plugins/azterisk.boot/"
  if [ -d windows ]; then
    cp -a windows "$pkgdir/usr/share/omarchy/plugins/azterisk.boot/"
  fi

  install -dm755 "$pkgdir/usr/bin"
  ln -sf "/usr/share/omarchy/plugins/azterisk.boot/scripts/omarchy-boot" "$pkgdir/usr/bin/omarchy-boot"
  ln -sf "/usr/share/omarchy/plugins/azterisk.boot/scripts/omarchy-boot-gui" "$pkgdir/usr/bin/omarchy-boot-gui"

  install -Dm644 omarchy-boot.desktop "$pkgdir/usr/share/applications/omarchy-boot.desktop"
  install -Dm644 scripts/org.omarchy.bootmanager.policy "$pkgdir/usr/share/polkit-1/actions/org.omarchy.bootmanager.policy"
  install -Dm644 LICENSE "$pkgdir/usr/share/licenses/$pkgname/LICENSE"
}
