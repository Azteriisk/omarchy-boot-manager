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
source=("git+https://github.com/Azteriisk/omarchy-boot-manager.git")
sha256sums=('SKIP')

package() {
  cd "$srcdir/omarchy-boot-manager"
  install -dm755 "$pkgdir/usr/share/omarchy/plugins/azterisk.boot"
  cp -a manifest.json scripts omarchy-boot.desktop README.md "$pkgdir/usr/share/omarchy/plugins/azterisk.boot/"

  install -dm755 "$pkgdir/usr/bin"
  ln -sf "/usr/share/omarchy/plugins/azterisk.boot/scripts/omarchy-boot" "$pkgdir/usr/bin/omarchy-boot"
  ln -sf "/usr/share/omarchy/plugins/azterisk.boot/scripts/omarchy-boot-gui" "$pkgdir/usr/bin/omarchy-boot-gui"

  install -Dm644 omarchy-boot.desktop "$pkgdir/usr/share/applications/omarchy-boot.desktop"
  install -Dm644 LICENSE "$pkgdir/usr/share/licenses/$pkgname/LICENSE"
}
