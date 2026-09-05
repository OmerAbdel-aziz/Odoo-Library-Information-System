from odoo import http
from odoo.http import request


class LibraryMapController(http.Controller):

    @http.route('/library_map/branches', type='json', auth='user')
    def branch_pins(self):
        branches = request.env['library.branch'].search([])
        return [b._pin_data() for b in branches]

    @http.route('/library_map/nearest', type='json', auth='user')
    def nearest(self, latitude=None, longitude=None, limit=1):
        try:
            lat = float(latitude)
            lng = float(longitude)
        except (TypeError, ValueError):
            return {'error': 'latitude and longitude are required.'}
        Branch = request.env['library.branch']
        return Branch.nearest_branch(lat, lng, limit=int(limit or 1))

    @http.route('/library_map/indoor', type='json', auth='user')
    def indoor(self, floor_id=None):
        Floor = request.env['library.floor']
        Shelf = request.env['library.shelf']
        floor = Floor.browse(int(floor_id)) if floor_id else Floor.search([], limit=1)
        if not floor.exists():
            return {'error': 'Floor not found.'}
        shelves = Shelf.search([('floor_id', '=', floor.id)])
        return {
            'floor': {'id': floor.id, 'name': floor.name, 'has_plan': bool(floor.plan_svg)},
            'shelves': [{
                'id': s.id,
                'name': s.name,
                'code': s.code,
                'section': s.section_id.name if s.section_id else False,
                'x': s.map_x, 'y': s.map_y,
                'width': s.map_width, 'height': s.map_height,
                'placed': s.map_placed,
            } for s in shelves],
        }

    @http.route('/library_map/floor_plan/<int:floor_id>', type='http', auth='user')
    def floor_plan(self, floor_id):
        floor = request.env['library.floor'].browse(floor_id)
        if not floor.exists() or not floor.plan_svg:
            return request.not_found()
        import base64
        return request.make_response(
            base64.b64decode(floor.plan_svg),
            headers=[('Content-Type', 'image/svg+xml')],
        )
