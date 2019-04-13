var markers = [];
var hnit = new Set();
// Initialize and add the map
function initMap() {
// The location of Uluru

    var map = new google.maps.Map(document.getElementById('map'), {
    center: {lng: -21.883949, lat : 64.133556},
    scrollwheel: true,
    zoom: 14,
    styles: [
          {
            featureType: 'poi',
            elementType: 'geometry',
            stylers: [{color: '#bcc9cc'}]
          },
          {
            featureType: 'poi',
            elementType: 'labels.text.fill',
            stylers: [{color: '#bcc9cc'}]
          },
          {
            featureType: 'poi.park',
            elementType: 'geometry.fill',
            stylers: [{color: '#bcc9cc'}]
          },
          {
            featureType: 'poi.park',
            elementType: 'labels.text.fill',
            stylers: [{color: '#bcc9cc'}]
          }
    ]
    });

    var script = document.createElement('script');

    map.data.setStyle(function(feature) {
      var color = 'gray';
      var opacity = 0.5;
      if (feature.getProperty('fill')) {
        color = feature.getProperty('fill');
      }
      if (feature.getProperty('opacity')) {
        opacity = feature.getProperty('opacity');
      }
      return /** @type {!google.maps.Data.StyleOptions} */({
        fillColor: color,
        fillOpacity: opacity,
        strokeWeight: 0,
        clickable: false
      });
    });
    

    var str = 'http://157.157.9.120/bins'
    var features = map.data.loadGeoJson(str);
    
    google.maps.event.addListener(map, 'dragend', function() {
        var bounds = map.getBounds()
        var upLeftlng = bounds.b.b
        var upLeftlat = bounds.f.b
        var downRightlng = bounds.b.f
        var downRightlat = bounds.f.f
        var str = 'http://157.157.9.120/litter?latmin='+ upLeftlat+'&latmax='+downRightlat+'&lonmin='+upLeftlng+'&lonmax='+ downRightlng;
        //map.data.loadGeoJson(str);
        
    //});
    
        fetch(str).then(response => {
        return response.json();
      }).then(data => {
        // Work with JSON data here
        var i
        for (i = 0; i < data.features.length; i ++) {
            var lat = data.features[i].geometry.coordinates[0];
            var lon = data.features[i].geometry.coordinates[1];
            var total = lat + lon;
            if (hnit.has(total)) {
                continue;
            }
            else {
                hnit.add(total)
                var myLatlng = new google.maps.LatLng(lon,lat);
                var marker = new google.maps.Marker({
                    position: myLatlng,
                    icon: 'trash.png'
                });
                marker.setMap(map);
                markers.push(marker);
            }
        }
            
            /*
            if (hnit.has(data.features[i].geometry.coordinates) == true) {
                console.log("Hallo")
            }
            else {
                hnit.add(data.features[i].geometry.coordinates)
                console.log(hnit)
            }}*/
        
        
      }).catch(err => {
        // Do something for an error here
        console.log(err)
      });
      

    });

    function setMapOnAll(map) {
        for (var i = 0; i < markers.length; i++) {
          markers[i].setMap(map);
        }
      }

    function clearMarkers() {
        setMapOnAll(null);
      }

    function showMarkers() {
        setMapOnAll(map);
      }


    //zoom level
    google.maps.event.addListener(map, 'zoom_changed', function() {
        var zoom = map.getZoom();
        console.log(zoom)
        if (zoom >= 1 && zoom <= 9) { 
            removeOverlay()
            console.log("1 to 9")
        } 
        else if (zoom > 9 && zoom <= 15) {
            clearMarkers()
            console.log("9 to 15")
        }
        else if (zoom > 15) {
            showMarkers()
            console.log("15 up")
            
        }
      });


    google.maps.event.addListener(map, 'click', function(event) {
        
        console.log(event.latLng);
        var r = confirm("Do you want to mark this loation!");  
        if (r == true) {
            placeMarker(event.latLng);
            var latitude = event.latLng.lat();
            var longitude = event.latLng.lng();
            var myLatlng = new google.maps.LatLng(latitude,latitude);
            var marker = new google.maps.Marker({
                    position: myLatlng,
                    icon: 'trash.png'
                });
                markers.push(marker);
            var url = 'http://157.157.9.120/litter?lat=' + latitude + '&lon=' + longitude;
            postForm(url)
            .then(data => reloadEverything())
        } 
        
        });
     
    function placeMarker(location) {
         var marker = new google.maps.Marker({
             position: location,
             map: map
         });
     }


    function postForm(url) {
        return fetch(url, {
            method: 'PUT', 
    })
        .then(response => response.json())
        .catch(error => console.error(error))
    }

    function hideMarkers(map, locations, markers) {
        /* Remove All Markers */
        while(markers.length){
            markers.pop().setMap(null);
        }

        console.log("Remove All Markers");
    }

    function reloadEverything() {
        map.data.forEach(function(feature) {
            map.data.remove(feature);
        });

        var str = 'http://157.157.9.120/bins'
        var features = map.data.loadGeoJson(str);
    }

}