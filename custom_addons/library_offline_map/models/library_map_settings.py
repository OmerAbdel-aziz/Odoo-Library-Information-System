from odoo import api, fields, models


class LibraryMapSettings(models.Model):
    _name = 'library.map.settings'
    _description = 'Library Map Settings'
    _rec_names_search = ['name']

    name = fields.Char(default='Library Map Configuration')
    tiles_url = fields.Char(
        string='Tiles URL Template', default='http://map-server:8080/tiles/{z}/{x}/{y}.pbf',
        help='Vector tile endpoint, e.g. local PMTiles/TileServer-GL URL.',
    )
    style_url = fields.Char(string='Style URL', default='http://map-server:8080/styles/basic.json')
    nominatim_url = fields.Char(string='Nominatim URL', default='http://map-nominatim:8080')
    valhalla_url = fields.Char(string='Valhalla URL', default='http://map-router:8002/route')
    maplibre_js_url = fields.Char(
        string='MapLibre JS URL', default='/library_offline_map/static/lib/maplibre-gl.js',
    )
    maplibre_css_url = fields.Char(
        string='MapLibre CSS URL', default='/library_offline_map/static/lib/maplibre-gl.css',
    )
    active = fields.Boolean(default=True)

    @api.model
    def _get_settings(self):
        settings = self.search([], limit=1)
        if not settings:
            settings = self.create({})
        return settings

    def action_test_tiles(self):
        self.ensure_one()
        return self._ping_service(self.tiles_url, 'Tiles endpoint is configured. Service check requires deployment.')

    def action_test_nominatim(self):
        self.ensure_one()
        return self._ping_service(self.nominatim_url, 'Nominatim is not reachable. Deploy the local service first.')

    def action_test_valhalla(self):
        self.ensure_one()
        return self._ping_service(self.valhalla_url, 'Valhalla is not reachable. Deploy the local service first.')

    def _ping_service(self, url, fallback_message):
        import urllib.request
        self.ensure_one()
        if not url:
            return {'type': 'ir.actions.client', 'tag': 'display_notification',
                    'params': {'title': 'Not configured', 'message': fallback_message, 'type': 'warning'}}
        try:
            urllib.request.urlopen(url, timeout=3)
            return {'type': 'ir.actions.client', 'tag': 'display_notification',
                    'params': {'title': 'Reachable', 'message': url, 'type': 'success'}}
        except Exception:
            return {'type': 'ir.actions.client', 'tag': 'display_notification',
                    'params': {'title': 'Unreachable', 'message': fallback_message, 'type': 'warning'}}
