import math

from odoo import api, fields, models


class LibraryBranchMap(models.Model):
    _inherit = 'library.branch'

    @staticmethod
    def _haversine_km(lat1, lon1, lat2, lon2):
        radius = 6371.0
        phi1, phi2 = math.radians(lat1), math.radians(lat2)
        dphi = math.radians(lat2 - lat1)
        dlambda = math.radians(lon2 - lon1)
        a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
        return 2 * radius * math.asin(math.sqrt(a))

    def _pin_data(self):
        self.ensure_one()
        return {
            'id': self.id,
            'name': self.name,
            'code': self.code,
            'street': self.street,
            'city': self.city,
            'phone': self.phone,
            'email': self.email,
            'latitude': self.latitude,
            'longitude': self.longitude,
            'opening_time': self.opening_time,
            'closing_time': self.closing_time,
            'manager': self.manager_id.name if self.manager_id else False,
        }

    @api.model
    def nearest_branch(self, latitude, longitude, limit=1):
        branches = self.search([('latitude', '!=', 0.0), ('longitude', '!=', 0.0)])
        ranked = sorted(
            branches,
            key=lambda b: self._haversine_km(latitude, longitude, b.latitude, b.longitude),
        )
        result = []
        for branch in ranked[:limit]:
            pin = branch._pin_data()
            pin['distance_km'] = round(
                self._haversine_km(latitude, longitude, branch.latitude, branch.longitude), 2
            )
            result.append(pin)
        return result
