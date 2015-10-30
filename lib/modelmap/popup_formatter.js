/**
 * Created by anna on 4/4/14.
 */

function formatLink(id) {
    "use strict";
    if (id) {
        return "<a href=\'?id=" + id + "\' target=\'_blank\'>Zoom inside</a>";
    }
    return "";
}

function p(text) {
    "use strict";
    return "<p class='popup centre'>" + text + "</p>";
}

function i(text) {
    "use strict";
    return "<span class='explanation'>" + text + "</span>";
}

function getPopup(feature, popupW, popupH) {
    "use strict";
    if (EDGE == feature.properties.type) {
        return;
    }
    var content = "<p class='emph centre'>" + feature.properties.name + "</p>" + p(i("id: ") + feature.properties.id),
        tr = (0 != (feature.properties.layer & TRANSPORT_MASK));
    if (REACTION == feature.properties.type) {
        var transport = tr ? p(i("Is a transport reaction.")) : "",
            ga_res = feature.properties.term ? p(feature.properties.term) : "",
            formula = feature.properties.f ? p(feature.properties.f) : "";
        content += formula + ga_res + transport;
    } else if (SPECIES == feature.properties.type) {
        var transported = tr ? p(i("Participates in a transport reaction.")) : "",
            ch = feature.properties.term ? p(feature.properties.term) : "", //p(formatChebi(feature.properties.term)),
            compartment = p(i("compartment: ") + feature.properties.c_name);
        if (feature.properties.f) {
            content += p(i("formula: ") + feature.properties.f);
        }
        content += compartment + ch + transported;
    } else if (COMPARTMENT == feature.properties.type) {
        content += feature.properties.term ? p(feature.properties.term) : ""; //p(formatGo(feature.properties.term));
        content += p(formatLink(feature.properties.id));
    }
    return L.popup({autoPan: true, keepInView: true, maxWidth: popupW, maxHeight: popupH, autoPanPadding: [1, 1]}).setContent(content);
}

function getLabel(feature) {
    "use strict";
    if (EDGE == feature.properties.type) {
        return null;
    }
    var label = "<p class='emph centre'>" + feature.properties.name + "</p>" + p(i("id: ") + feature.properties.id),
        tr = (0 != (feature.properties.layer & TRANSPORT_MASK));
    if (REACTION == feature.properties.type) {
        var transport = tr ? p(i("Is a transport reaction.")) : "",
            formula = feature.properties.f ? p(feature.properties.f) : ""; //p(formatFormula(feature.properties.rev, feature.properties.rs, feature.properties.ps));
        label += formula + transport;
    }
    if (SPECIES == feature.properties.type) {
        var transported = tr ? p(i("Participates in a transport reaction.")) : "",
            compartment = p(i("compartment: ") + feature.properties.c_name);
        label += compartment + transported;
    }
    return label;
}

function highlightCircle(centre, r) {
    "use strict";
    return L.circle(centre, r, {
        color: "#fff700",
        fillColor: "#fff700",
        fillOpacity: 0.7,
        opacity: 1,
        weight: 2,
        fill: true,
        clickable: false
    });
}

function search(map, name2popup, name2zoom, mapId) {
    "use strict";
    var srch = $("#tags_" + mapId).val();
    if (srch && name2popup.hasOwnProperty(srch)) {
        var zoom = map.getZoom(),
            zooms = name2zoom[srch];
        if (zooms[0] > zoom) {
            map.setZoom(zooms[0]);
        } else if (zoom > zooms[1]) {
            map.setZoom(zooms[1]);
        }
        name2popup[srch].openOn(map);
    }
}

function add(map, key, value) {
    "use strict";
    if (map.hasOwnProperty(key)) {
        map[key].push(value);
    } else {
        map[key] = [value];
    }
}