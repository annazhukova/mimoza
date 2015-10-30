/**
 * Created by anna on 6/17/14.
 */

var MARGIN = 156,
    MAP_DIMENSION_SIZE = 512,
    EDGE = 0,
    SPECIES = 1,
    COMPARTMENT = 3,
    REACTION = 2,
    BG_SPECIES = 4,
    BG_REACTION = 5,
    BG_COMPARTMENT = 6,
    BG = [BG_SPECIES, BG_REACTION, BG_COMPARTMENT],
    TRANSPORT = "transport to outside",
    MIN_LABEL_SIZE = 10,
    MAX_LABEL_SIZE = 16,
    TRANSPORT_MASK = 1,
    NON_TRANSPORT_MASK = 1 << 1,
    UBIQUITOUS_MASK = 1 << 2;

function pnt2layer(map, compLayer, ubLayer, feature, fromZoom, toZoom, coords, minZoom, cId,
                   popupW, popupH, name2popup, name2zoom, name2selection) {
    "use strict";
    var e = feature.geometry.coordinates,
        scaleFactor = Math.pow(2, fromZoom),
        w = feature.properties.w;
    if (EDGE == feature.properties.type) {
        var props = {
            color: feature.properties.color,
            opacity: 1,
            weight: Math.max(Math.min(w / 2, 10), 2),
            lineCap: 'round',
            lineJoin: 'round',
            clickable: false,
            fill: false,
            zIndexOffset: 0,
            riseOnHover: false
        };
        if (0 != (feature.properties.layer & TRANSPORT_MASK)) {
            props.opacity = 0.5;
            props.dashArray = '2, 3';
            props.weight = Math.max(Math.min(w / 4, 8), 1.5)
        }
        return L.polyline(e.map(function (coord) {
            return map.unproject(coord, 1);
        }), props);
    }
    if (SPECIES == feature.properties.type || BG_SPECIES == feature.properties.type) {
        w /= Math.sqrt(2);
    }
    var x = e[0], y = e[1],
        is_bg = -1 !== BG.indexOf(feature.properties.type),
        props = {
            name: feature.properties.name,
            title: feature.properties.name,
            alt: feature.properties.name,
            id: feature.properties.id,
            color: BG_COMPARTMENT != feature.properties.type ? 'white': feature.properties.color,
            fillColor: feature.properties.color,
            fillOpacity: BG_COMPARTMENT == feature.properties.type ? 0 : (is_bg ? 0.3: 1),
            opacity: 1,
            weight: BG_COMPARTMENT != feature.properties.type ? (is_bg ? 0: Math.min(1, w / 10 * scaleFactor)): 4,
            fill: true,
            clickable: !is_bg,
            zIndexOffset: is_bg ? 6 : 0,
            riseOnHover: !is_bg
        },
        h = (BG_COMPARTMENT == feature.properties.type || COMPARTMENT == feature.properties.type) ?
            feature.properties.h : w,
        bounds = new L.LatLngBounds(map.unproject([x - w, y + h], 1), map.unproject([x + w, y - h], 1)),
        centre = map.unproject([x, y], 1),
        ne = bounds.getNorthEast(),
        sw = bounds.getSouthWest(),
        r = w * 40075000 * Math.cos(centre.lat * (Math.PI / 180)) / Math.pow(2, minZoom + 8);
    if (BG_COMPARTMENT == feature.properties.type || COMPARTMENT == feature.properties.type) {
        if (coords[2] == null || (BG_COMPARTMENT == feature.properties.type && cId == feature.properties.c_id
            || COMPARTMENT == feature.properties.type && cId == feature.properties.id)) {
            coords[2] = centre;
        }
    }
    if (BG_REACTION == feature.properties.type) {
        return L.rectangle(bounds, props);
    }
    if (BG_SPECIES == feature.properties.type) {
        return L.circle(centre, r, props);
    }
    var node = null;
    if (REACTION == feature.properties.type || COMPARTMENT == feature.properties.type || BG_COMPARTMENT == feature.properties.type) {
        node = L.rectangle(bounds, props);
    } else if (SPECIES == feature.properties.type) {
        node = L.circle(centre, r, props);
    } else {
        return null;
    }
    coords[0][0] = coords[0][0] == null ? sw.lat : Math.min(coords[0][0], sw.lat);
    coords[0][1] = coords[0][1] == null ? sw.lng : Math.max(coords[0][1], sw.lng);
    coords[1][0] = coords[1][0] == null ? ne.lat : Math.max(coords[1][0], ne.lat);
    coords[1][1] = coords[1][1] == null ? ne.lng : Math.min(coords[1][1], ne.lng);

    var popup = undefined,
        label = undefined;

    function addSelectionCircles(key) {
        if (!name2selection.hasOwnProperty(key)) {
            name2selection[key] = L.featureGroup();
        }
        var selection_layer = name2selection[key];
        selection_layer.addLayer(highlightCircle(centre, r));
        map.on('popupopen', function (e) {
            if (e.popup === popup) {
                if (map.hasLayer(ubLayer)) {
                    compLayer.addLayer(selection_layer);
                }
            }
        });
        map.on('popupclose', function (e) {
            if (e.popup === popup) {
                compLayer.removeLayer(selection_layer);
            }
        });
    }

    if (BG_COMPARTMENT != feature.properties.type) {
        popup = getPopup(feature, popupW, popupH);
        popup.setLatLng(centre);
        node.bindPopup(popup);
        if (SPECIES == feature.properties.type) {
            addSelectionCircles(feature.properties.id);
        }
        [feature.properties.name, feature.properties.id, feature.properties.t, feature.properties.lbl].forEach(function (key) {
            if (key) {
                key = key.replace(new RegExp('(<sub>)|(</sub>)', 'g'), '');
                if (!name2popup.hasOwnProperty(key)) {
                    name2popup[key] = popup;
                }
                if (!name2zoom.hasOwnProperty(key)) {
                    name2zoom[key] = [fromZoom, toZoom];
                }
            }
        });
        label = getLabel(feature);
        node.bindLabel(label, {direction: "auto", opacity: 1});
    }

    node = L.featureGroup([node]);


    var lbl = (REACTION == feature.properties.type ? feature.properties.id :
                (SPECIES == feature.properties.type ? feature.properties.lbl : feature.properties.name)),
        minLabelZoom = Math.max(fromZoom,
            Math.ceil(Math.log(Math.max(MIN_LABEL_SIZE / h, lbl.length / (2 * w))) / Math.LN2)
        );
    if (minLabelZoom <= toZoom) {
        var size = MIN_LABEL_SIZE;//Math.min(Math.max(Math.round(w * Math.pow(2, minLabelZoom - 1)), MIN_LABEL_SIZE), MAX_LABEL_SIZE);

        var marker = L.marker(centre,
            {
                icon: L.divIcon({
                    className: 'element-label',
                    html: "<span class=\"label-span\" style=\"font-size:" + size +
                    "px;line-height:" + (size + 2) + "px;color:" +
                    (BG_COMPARTMENT == feature.properties.type ? feature.properties.color : "black") + "\">"
                    + lbl + "</span>",
                    iconSize: [w * Math.pow(2, minLabelZoom + 1), (size + 3)],
                    zIndexOffset: 0,
                    riseOnHover: false,
                    riseOffset: 0
                })
            }
        );
        if (popup != undefined) {
            marker.bindPopup(popup);
        }
        if (label != undefined) {
            marker.bindLabel(label, {direction: "auto", opacity: 1});
        }

        if (typeof map.getZoom() !== 'undefined') {
            if (map.getZoom() >= minLabelZoom && map.getZoom() <= toZoom) {
                node.addLayer(marker);
            }
        } else if (fromZoom == minLabelZoom) {
            node.addLayer(marker);
        }
        map.on('zoomend', function (e) {
            if (map.getZoom() >= minLabelZoom && map.getZoom() <= toZoom) {
                if (!node.hasLayer(marker)) {
                    node.addLayer(marker);
                }
            } else {
                node.removeLayer(marker);
            }
        });
    }

    if (popup != undefined) {
        node.bindPopup(popup);
    }
    if (label != undefined) {
        node.bindLabel(label, {direction: "auto", opacity: 1});
    }

    if (COMPARTMENT == feature.properties.type) {
        map.on('zoomend', function (e) {
            var mapBounds = map.getBounds();
            if (map.getZoom() > minZoom + 2 && map.getBounds().intersects(bounds) && (map.getZoom() == map.getMaxZoom()
            || bounds.contains(mapBounds.getSouthWest()) && bounds.contains(mapBounds.getNorthEast()))) {
                    window.location.href = "?id=" + feature.properties.id;
            }
        });
    }
    return node;
}

function matchesCompartment(cId, feature) {
    "use strict";
    if (TRANSPORT === cId) {
        return (0 == (feature.properties.layer & NON_TRANSPORT_MASK))
            && (0 != (feature.properties.layer & TRANSPORT_MASK));
    }
    return (0 == (feature.properties.layer & TRANSPORT_MASK)) || (0 != (feature.properties.layer & NON_TRANSPORT_MASK));
}

function getFilteredJson(map, compLayer, ubLayer, jsn, name2popup, name2zoom, fromZoom, toZoom, mapId, coords, minZoom,
                         cId, filterFunction) {
    "use strict";
    var name2selection = {},
        $map = $('#' + mapId),
        popupW = $map.width() - 2,
        popupH = $map.height() - 2;
    return L.geoJson(jsn, {
        pointToLayer: function (feature, latlng) {
            return pnt2layer(map, compLayer, ubLayer, feature, fromZoom, toZoom, coords, minZoom, cId, popupW, popupH,
                name2popup, name2zoom, name2selection);
        },
        filter: function (feature, layer) {
            return filterFunction(feature);
        },
        onEachFeature: function(feature, layer) {
            feature.layer = layer;
        }
    });
}

function loadGeoJson(map, json, fromZoom, toZoom, ubLayer, compLayer, superLayer, mapId, cId, name2popup, name2zoom, coords,
                     minZoom, inZoom, mask) {
    "use strict";
    var specificJson = getFilteredJson(map, compLayer, ubLayer, json, name2popup, name2zoom, fromZoom, toZoom, mapId,
            coords, minZoom, inZoom == null ? cId: inZoom,
            function (feature) {
                return (0 != (feature.properties.layer & mask)) &&
                    (0 == (feature.properties.layer & UBIQUITOUS_MASK))
                    && matchesCompartment(cId, feature);
            }
        ),
        ubiquitousJson = getFilteredJson(map, compLayer, ubLayer, json, name2popup, name2zoom, fromZoom, toZoom, mapId,
            coords, minZoom, inZoom == null ? cId: inZoom,
            function (feature) {
                return (0 != (feature.properties.layer & mask)) &&
                    (0 != (feature.properties.layer & UBIQUITOUS_MASK))
                    && matchesCompartment(cId, feature);
            }
        );
    if (typeof map.getZoom() === 'undefined' && fromZoom <= minZoom && minZoom <= toZoom
        || fromZoom <= map.getZoom() && map.getZoom() <= toZoom) {
        if (superLayer != null) {
            if (map.hasLayer(compLayer)) {
                superLayer.addLayer(specificJson);
                if (map.hasLayer(ubLayer)) {
                    superLayer.addLayer(ubiquitousJson);
                }
            }
        } else {
            compLayer.addLayer(specificJson);
            if (map.hasLayer(ubLayer)) {
                compLayer.addLayer(ubiquitousJson);
            }
        }
    }
    if (fromZoom > minZoom || toZoom < map.getMaxZoom()) {
        map.on('zoomend', function (e) {
            // if we are about to zoom in/out to this geojson
            if (fromZoom <= map.getZoom() && map.getZoom() <= toZoom) {
                if (superLayer != null) {
                    if (map.hasLayer(compLayer)) {
                        superLayer.addLayer(specificJson);
                        if (map.hasLayer(ubLayer)) {
                            superLayer.addLayer(ubiquitousJson);
                        }
                    }
                } else {
                    compLayer.addLayer(specificJson);
                    if (map.hasLayer(ubLayer)) {
                        compLayer.addLayer(ubiquitousJson);
                    }
                }
            } else {
                if (superLayer != null) {
                    superLayer.removeLayer(specificJson);
                    superLayer.removeLayer(ubiquitousJson);
                } else {
                    compLayer.removeLayer(specificJson);
                    compLayer.removeLayer(ubiquitousJson);
                }
            }
        });
    }
    map.on('overlayadd', function(e) {
        if (fromZoom <= map.getZoom() && map.getZoom() <= toZoom) {
            if (e.layer === ubLayer) {
                if (superLayer != null) {
                    if (map.hasLayer(compLayer)) {
                        superLayer.addLayer(ubiquitousJson);
                    }
                } else {
                    compLayer.addLayer(ubiquitousJson);
                }
            } else if (superLayer != null && e.layer === compLayer) {
                superLayer.addLayer(specificJson);
                if (map.hasLayer(ubLayer)) {
                    superLayer.addLayer(ubiquitousJson);
                }
            }
        }
    });
    map.on('overlayremove', function(e) {
        if (fromZoom <= map.getZoom() && map.getZoom() <= toZoom) {
            if (e.layer === ubLayer) {
                if (superLayer != null) {
                    superLayer.removeLayer(ubiquitousJson);
                } else {
                    compLayer.removeLayer(ubiquitousJson);
                }
            } else if (superLayer != null && e.layer === compLayer) {
                superLayer.removeLayer(specificJson);
                superLayer.removeLayer(ubiquitousJson);
            }
        }
    });
    return [specificJson.getLayers().length > 0, ubiquitousJson.getLayers().length > 0];
}
