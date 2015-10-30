/**
 * Created by anna on 12/12/13.
 */

var UB_LAYER_NAME = "<i>Ubiquitous metabolites</i>",
    TRANSPORT_LAYER_NAME = "<i>Transport reactions</i>",
    LEAFLET_POPUP_MARGIN = 10,
    ALL_COMPARTMENTS = 'all_comp_view',
    DEFAULT_LAYER = 'default';

function adjustMapSize(mapId) {
    "use strict";
    var MIN_DIMENTION_SIZE = 512,
        width = Math.max(MIN_DIMENTION_SIZE, Math.round(($(window).width() * 0.7))),
        height = Math.max(MIN_DIMENTION_SIZE, Math.round(($(window).height() * 0.6)));
    return adjustMapDivSize(mapId, width, height);
}

function adjustMapDivSize(mapId, width, height) {
    "use strict";
    var $map_div = $("#" + mapId),
        old_height = $map_div.height(),
        old_width = $map_div.width();
    if (old_width != width || old_height != height) {
        $map_div.css({
            'height': height,
            'width': width
        });
        $(".leaflet-popup").css({
            'maxHeight': height,
            'maxWidth': width
        });
        $(".leaflet-popup-content").css({
            'maxHeight': height - LEAFLET_POPUP_MARGIN,
            'maxWidth': width - LEAFLET_POPUP_MARGIN
        });
    }
    return Math.min(width, height);
}

function getTiles(img, minZoom, maxZoom) {
    "use strict";
    return L.tileLayer(img, {
        continuousWorld: true,
        noWrap: true,
        tileSize: 256,
        maxZoom: maxZoom,
        minZoom: minZoom,
        tms: true,
        updateWhenIdle: true,
        reuseTiles: true
    });
}

function handlePopUpClosing(map) {
    "use strict";
    var popup = null;
    map.on('popupopen', function (e) {
        popup = e.popup;
    });
    map.on('dragstart', function (e) {
        if (popup) {
            map.closePopup(popup);
            popup.options.keepInView = false;
            map.openPopup(popup);
            popup.options.keepInView = true;
            popup = null;
        }
    });
}

function updateMapBounds(coords, commonCoords, map) {
    coords[0][0] = coords[0][0] == null ? commonCoords[0][0] : Math.min(coords[0][0], commonCoords[0][0]);
    coords[0][1] = coords[0][1] == null ? commonCoords[0][1] : Math.max(coords[0][1], commonCoords[0][1]);
    coords[1][0] = coords[1][0] == null ? commonCoords[1][0] : Math.max(coords[1][0], commonCoords[1][0]);
    coords[1][1] = coords[1][1] == null ? commonCoords[1][1] : Math.min(coords[1][1], commonCoords[1][1]);

    var mapW = coords[1][0] - coords[0][0],
        mapH = coords[0][1] - coords[1][1],
        margin = Math.max(mapW, mapH) * 0.1;

    coords[0][0] -= margin;
    coords[0][1] += margin;
    coords[1][0] += margin;
    coords[1][1] -= margin;

    map.setMaxBounds(coords);
}

function addAttribution(map) {
    var attrControl = L.control.attribution({
        position: 'bottomleft',
        prefix: false
    });
    attrControl.addAttribution(
        //'<p><span style="background-color:#E37B6F">&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;</span>/<span style="background-color:#B4B4B4">&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;</span> - not generalized/ubiquitous metabolites; <span style="background-color:#79A8C9">&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;</span> - not generalized reactions.</p>' +
        '<p>Ubiquitous metabolites are not shown in order to improve the performance.</p>'
    );
    attrControl.addTo(map);
}

function initializeMap(cId2jsonData, mapId, compIds, cId2outside, CIdsWOUbs, hiddenCIds, layer2mask, invisibleLayers) {
    "use strict";
    var size = adjustMapSize(mapId),
        layers = [],
        minGeneralizedZoom = Math.max(1, Math.round(size / MAP_DIMENSION_SIZE)),
        maxGeneralizedZoom = minGeneralizedZoom + 1,
        minSpecificZoom = maxGeneralizedZoom + 1,
        maxSpecificZoom = minSpecificZoom + 5,
        ubLayer = L.layerGroup(),
        transportLayer = L.layerGroup(),
        overlays = {},
        cIds = {},
        cId = getParameter("id"),
        inZoom = getParameter("zoom"),
        curZoom = inZoom == null ? maxGeneralizedZoom : minSpecificZoom,
        outCId = null,
        jsonData;
    if (compIds && typeof Object.keys(compIds) !== 'undefined' && Object.keys(compIds).length > 0
        && (cId == null || !compIds.hasOwnProperty(cId))) {
        cId = compIds.hasOwnProperty(ALL_COMPARTMENTS) ? ALL_COMPARTMENTS: Object.keys(compIds)[0];
    }
    if (hiddenCIds.indexOf(cId) > - 1) {
        $("#" + mapId).hide();
        $("#search").hide();
        $("#explanations").html('<p>We could not visualize this compartment as it is too huge ;(</p>');
        return;
    }
    if (cId != null) {
        cIds[cId] = compIds[cId];
        jsonData = cId2jsonData[cId];
        if (cId in cId2outside) {
            outCId = cId2outside[cId];
        }
        var $c_menu = $(".menu_" + cId);
        $c_menu.css("font-weight","Bold");
        $c_menu.click(function () {return false;});
    }
    if (inZoom != null && !compIds.hasOwnProperty(inZoom)) {
        inZoom = null;
    }
    if (typeof jsonData === 'undefined' || jsonData.length <= 0) {
        return null;
    }
    var tiles = getTiles("lib/modelmap/white.jpg", minGeneralizedZoom, maxSpecificZoom),
        grayTiles = getTiles("lib/modelmap/gray.jpg", minGeneralizedZoom, maxSpecificZoom),
        name2layer = {};
    for (var i = 0; i < layer2mask.length; i++) {
        var l = L.layerGroup();
        name2layer[layer2mask[i][0]] = l;
        if (invisibleLayers == null || $.inArray(layer2mask[i][0], invisibleLayers) == -1) {
            layers.push(l);
        }
    }
    layers.push(ubLayer);
    layers.push(tiles);
    layers.push(transportLayer);
    var map = L.map(mapId, {
        maxZoom: maxSpecificZoom,
        minZoom: outCId != null ? minGeneralizedZoom - 1 : minGeneralizedZoom,
        zoom: curZoom,
        attributionControl: false,
        padding: [MARGIN, MARGIN],
        layers: layers,
        crs: L.CRS.Simple
    });

    if (CIdsWOUbs.indexOf(cId) > - 1) {
        addAttribution(map);
    }
    handlePopUpClosing(map);
    var name2popup = {},
        name2zoom = {},
        maxLoadedZoom = inZoom == null ? maxGeneralizedZoom : maxSpecificZoom,
        coords = [
            [null, null],
            [null, null]
        ],
        commonCoords = [
            [null, null],
            [null, null],
            null
        ],
        ubJSON = false,
        inJSON = false,
        outJSON = false,
        jsonArray;


    //var searchCtrl = L.control.fuseSearch({
    //    position : 'topright',
    //    title : '',
    //    placeholder : 'Search',
    //    maxResultLength : 1,
    //    showInvisibleFeatures : false,
    //    showResultFct: function(feature, container) {
    //        var props = feature.properties;
    //        var name = L.DomUtil.create('b', null, container);
    //        name.innerHTML = props.name;
    //        container.appendChild(L.DomUtil.create('br', null, container));
    //        container.appendChild(document.createTextNode(props.details));
    //    }
    //});
    //searchCtrl.addTo(map);

    function loadElements(json, fromZoom, toZoom, coords) {
        for (var i = 0; i < layer2mask.length; i++) {
            l = name2layer[layer2mask[i][0]];
            var mask = layer2mask[i][1];
            jsonArray = loadGeoJson(map, json, fromZoom, toZoom, ubLayer, l, null, mapId, cId,
                name2popup, name2zoom, coords, minGeneralizedZoom, inZoom, mask);

            ubJSON |= jsonArray[1];
            jsonArray = loadGeoJson(map, json, fromZoom, toZoom, ubLayer, transportLayer, l, mapId, TRANSPORT,
                name2popup, name2zoom, coords, minGeneralizedZoom, inZoom, mask);
            ubJSON |= jsonArray[1];
            outJSON |= jsonArray[0] || jsonArray[1];
            //searchCtrl.indexFeatures(json.features, ['name', 'id']);
        }
    }

    // load common elements
    loadElements(jsonData[0], minGeneralizedZoom, maxSpecificZoom, commonCoords);
    // load generalized elements
    loadElements(jsonData[1], minGeneralizedZoom, maxGeneralizedZoom, coords);

    if (curZoom >= minSpecificZoom) {
        loadElements(jsonData[2], minSpecificZoom, maxSpecificZoom, coords);
    }

    updateMapBounds(coords, commonCoords, map);
    if (commonCoords[0][0] != null && commonCoords[1][0] != null) {
        if (commonCoords[2] != null) {
            map.setView(commonCoords[2], curZoom);
        } else {
            var c = new L.LatLngBounds(commonCoords[0], commonCoords[1]).getCenter();
            map.setView(c, curZoom);
        }
    } else {
        map.setView([0, 0], curZoom);
    }

    var $map_div = $("#" + mapId);
    $map_div.bind('resize', function(){
        var h = $map_div.height(),
            w = $map_div.width();
        $(".leaflet-popup").css({
            'maxHeight': h,
            'maxWidth': w
        });
        $(".leaflet-popup-content").css({
            'maxHeight': h - LEAFLET_POPUP_MARGIN,
            'maxWidth': w - LEAFLET_POPUP_MARGIN
        });
        map.invalidateSize();
        map.setView(map.getCenter(), map.getZoom());
    });

    if (layer2mask.length > 1) {
        for (var i = 0; i < layer2mask.length; i++) {
            var l_name = layer2mask[i][0];
            if (l_name != DEFAULT_LAYER) {
                overlays[l_name] = name2layer[l_name];
            }
        }
    }
    if (ubJSON) {
        overlays[UB_LAYER_NAME] = ubLayer;
    }
    if (outJSON) {
        overlays[TRANSPORT_LAYER_NAME] = transportLayer;
    }
    var baseLayers = {
        "White background": tiles,
        "Gray background": grayTiles
        },
        control = L.control.layers(baseLayers, overlays);
    control.addTo(map);

    initializeAutocomplete(name2popup, name2zoom, map, mapId);

    map.on('zoomend', function (e) {
        if (outCId != null && map.getZoom() == map.getMinZoom()) {
            window.location.href = "?id=" + outCId + (cId == null ? "" : ("&zoom=" + cId));
        }
        // if we are about to zoom in/out to this geojson
        if (map.getZoom() > maxLoadedZoom) {
            // load specific elements
            loadElements(jsonData[2], minSpecificZoom, maxSpecificZoom, coords);
            updateMapBounds(coords, commonCoords, map);
            var updateControl = false;
            if (!overlays.hasOwnProperty(UB_LAYER_NAME) && ubJSON) {
                overlays[UB_LAYER_NAME] = ubLayer;
                updateControl = true;
            }
            // outside transport should already be visible on the general zoom level,
            // so no need to update the control
            if (updateControl) {
                control.removeFrom(map);
                control = L.control.layers(baseLayers, overlays);
                control.addTo(map);
            }
            maxLoadedZoom = maxSpecificZoom;
            initializeAutocomplete(name2popup, name2zoom, map, mapId);
        }
    });

    $('#a-' + mapId).on('click',function(){
        window.setTimeout(function () {
            map.invalidateSize();
        });
    });

    return map;
}


function initializeAutocomplete(name2popup, name2zoom, map, mapId) {
    "use strict";
    var searchForm = document.getElementById('search_form_' + mapId);
    if (searchForm !== null) {
        var $tags = $("#tags_" + mapId);
        $tags.autocomplete({
            source: Object.keys(name2popup),
            autoFocus: true
        });
        $tags.keypress(function (e) {
            var code = e.keyCode || e.which;
            if (code === $.ui.keyCode.ENTER) {
                search(map, name2popup, name2zoom, mapId);
                e.preventDefault();
            }
        });
        searchForm.onclick = function () {
            search(map, name2popup, name2zoom, mapId);
        };
    }
}


function overlay() {
    "use strict";
    var el = document.getElementById("overlay");
    var $embed_w = $("#embed-size-width"),
        $embed_h = $("#embed-size-height");
    update_embed_value($embed_w.val(), $embed_h.val());
    el.style.visibility = (el.style.visibility === "visible") ? "hidden" : "visible";
    $embed_w.focusout(function() {
        var w = 800;
        if ($embed_w.val()) {
            var newW = parseInt($embed_w.val());
            if (!isNaN(newW) && newW > 0) {
                w = newW;
            } else {
                $embed_w.val(w);
            }
        } else {
            $embed_w.val(w);
        }
        update_embed_value(w, $embed_h.val());
    });
    $embed_h.focus(function() {
        $embed_h.select();
    });
    $embed_w.focus(function() {
        $embed_w.select();
    });
    $embed_h.focusout(function() {
        var h = 800;
        if ($embed_h.val()) {
            var newH = parseInt($embed_h.val());
            if (!isNaN(newH) && newH > 0) {
                h = newH;
            } else {
                $embed_h.val(h);
            }
        } else {
            $embed_h.val(h);
        }
        update_embed_value($embed_w.val(), h);
    });
    $("#embed-html-snippet").focus(function() {
        $(this).select();
    });
}


function getParameter(name){
  var regexS = "[\\?&]" + name + "=([^&#]*)";
  var regex = new RegExp(regexS);
  var results = regex.exec(window.location.href);
  if(results == null)
    return null;
  else
    return results[1];
}


function update_embed_value(w, h) {
    "use strict";
    var cId = getParameter(),
        url = $("#embed-url").val();
    if (cId) {
        url += "?id=" + cId;
    }
    $("#embed-html-snippet").val("<iframe src=\"" + url + "\" width=\"" + w + "\" height=\"" + h
        + "\" frameborder=\"0\" style=\"border:0\"></iframe>");
}