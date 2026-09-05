import { Component, onWillStart, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { rpc } from "@web/core/network/rpc";

export class IndoorMap extends Component {
    static template = "library_offline_map.IndoorMap";
    static props = {
        action: { type: Object, optional: true },
        actionId: { type: Number, optional: true },
    };

    setup() {
        const params = this.props.action?.params || {};
        this.state = useState({
            floor: null,
            shelves: [],
            highlightId: params.highlight_shelf_id || null,
            error: null,
        });
        this.floorId = params.floor_id || null;
        onWillStart(async () => {
            try {
                const data = await rpc("/library_map/indoor", { floor_id: this.floorId });
                if (data.error) {
                    this.state.error = data.error;
                    return;
                }
                this.state.floor = data.floor;
                this.state.shelves = data.shelves;
            } catch (e) {
                this.state.error = "Could not load the indoor map.";
            }
        });
    }

    shelfClass(shelf) {
        let cls = "lib-shelf";
        if (!shelf.placed) {
            cls += " lib-shelf-unplaced";
        }
        if (this.state.highlightId && shelf.id === this.state.highlightId) {
            cls += " lib-shelf-highlight";
        }
        return cls;
    }
}

registry.category("actions").add("library_indoor_map", IndoorMap);
