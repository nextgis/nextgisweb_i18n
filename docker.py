from ngwdocker import PackageBase
from ngwdocker.base import AppImage


class Package(PackageBase):
    target_ngw = False


@AppImage.on_config.handler
def on_config(event):
    event.image.config_set(
        'core', 'locale.external_path',
        '${NGWROOT}/package/nextgisweb_i18n')