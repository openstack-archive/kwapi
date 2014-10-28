function startRefreshing() {
    stopRefreshing();
    timer = setInterval('reloadAllImages("last")', 5000);
}

function startRefreshingFixedStart() {
    stopRefreshing();
    timer = setInterval('reloadAllImages("fixedStart")', 5000);
}

function stopRefreshing() {
    if(typeof timer != 'undefined') {
        clearInterval(timer);
    }
}

function modifyPeriod(start, end) {
    $('.graph').each(function() {
        var src = $(this).attr('src');
        var probes = '';
        if(src.indexOf('?') != -1) {
            probes = src.substring(src.indexOf('?'));
            src = src.substring(0, src.indexOf('?'));
        }
        var src_list = src.split('/');
        src_list.pop();
        src_list.pop();
        src_list.pop();
        $(this).attr('src', src_list.join('/') + '/' + start + '/' + end + '/' + probes);
    });
}

function reloadImage(img, mode) {
    var src = img.attr('src');
    var probes = '';
    if(src.indexOf('?') != -1) {
        probes = src.substring(src.indexOf('?'));
        src = src.substring(0, src.indexOf('?'));
    }
    var src_list = src.split('/');
    src_list.pop();
    var end = src_list.pop();
    var start = src_list.pop();
    var interval = end - start;
    var newEnd = Math.ceil(Date.now() / 1000);
    if(mode == 'last') {
        var newStart = newEnd - interval;
    } else if(mode == 'fixedStart') {
        var newStart = start;
    }
    img.attr('src', src_list.join('/') + '/' + newStart + '/' + newEnd + '/' + probes);
}

function reloadAllImages(mode) {
    $('.graph').each(function() {
        reloadImage($(this), mode);
    });
}

function selectJobId() {
    deselectAll();
    job = $('#job-field').val();
    if(!job) {
        return;
    }
    $('#loading-div-background').show();
    $.ajax({
        url: '/nodes/' + job + '/',
        dataType: 'json',
        success: function(data) {
            stopRefreshing();
            if(data.started_at == 'Undefined' ||
            data.started_at >= Math.ceil(Date.now() / 1000)) {
                alert('Job has not started');
                $('#loading-div-background').hide();
                startRefreshing();
                return;
            }
            var items = data.nodes;
            if(items.length === 0) {
                alert('No hosts found');
            }
            var selected = [];
            $.each(items, function(i, e) {
                e = e.split('.');
                e = e[1] + '.' + e[0];
                probe = probeInSelect(e);
                if($.inArray(probe, selected) != -1) {
                    return;
                }
                if(probe) {
                    selected[selected.length] = probe;
                    $('select').trigger({
                        type: 'select2-selecting',
                        val: probe
                    });
                    $('select').select2('val', selected);
                    //if network probe add the reverse probe
                    var switchProbeFields = probe.split('_');
                    if(switchProbeFields.length > 1) {
                        var site = switchProbeFields[0].split('.')[0];
                        var sw = switchProbeFields[0].split('.')[1];
                        selected[selected.length] = site + '.' + switchProbeFields[1] + '_' + sw;
                        $('select').trigger({
                            type: 'select2-selecting',
                            val: probe
                        });
                        $('select').select2('val', selected);
                    }
                }
                else {
                    $('#not-found').append('<li>' + e + ' is not monitored</li>');
                    $('#probes-not-found').show();
                }
            })
            $('#loading-div-background').hide();
            var fixedStart = false;
            if(data.stopped_at == 'Undefined') {
                data.stopped_at = Math.ceil(Date.now() / 1000);
                fixedStart = true
            }
            modifyPeriod(data.started_at, data.stopped_at);
            if(fixedStart) {
                startRefreshingFixedStart();
            }
            $('.active').removeClass('active');
        },
        timeout: 10000,
        error: function(jqXHR, status, errorThrown) {
            alert('Timeout or Error occured');
            $('#loading-div-background').hide();
        }
    });
}

function selectAll() {
    $('.activable').addClass('active');
    startRefreshing();
    deselectAll();
    var selected = [];
    $('select option').each(function(i, e) {
        selected[selected.length] = $(e).attr('value');
        $('select').trigger({
            type: 'select2-selecting',
            val: $(e).attr('value')
        });
    });
    $('select').select2('val', selected);
    $('#summary').attr('src', "/network/summary-graph/1411124629/1411124929/");
    reloadAllImages('last');
    $('#zip').text('Download all probes RRD');
}

function deselectAll() {
    $('.activable').addClass('active');
    startRefreshing();
    $('select').each(function () {
        $(this).select2('val', '');
    });
    var selected = [];
    $('select option').each(function(i, e) {
        selected[selected.length] = $(e).attr('value');
        $('select').trigger({
            type: 'select2-removing',
            val: $(e).attr('value')
        });
    });
    $('#summary').attr('src', "/network/summary-graph/1411124629/1411124929/");
    reloadAllImages('last');
    $('#probes-not-found').hide();
    $('#not-found').empty();
    $('#zip').text('Download all probes RRD');
}

function probeInSelect(probe) {
    var found = false;
    probeSplit = probe.split('-');
    probeBase = probeSplit[0];
    probeNum = probeSplit[probeSplit.length-1];
    $('select option').each(function(i, e) {
        //if network style (Switch_Probe)
        if($(e).attr('value').split('_').length > 1){
            //check the 2 parts
            switchProbesSplit = $(e).attr('value').split('_');
            for(var j=0; j < 2; j++) {
                if(switchProbesSplit[j].indexOf(probe) > -1){
                    found = $(e).attr('value');
                    return found;
                }
            }
        }
        else{
            //Traditionnal style (Probe-Nb)
            multiProbeSplit = $(e).attr('value').split('-');
            multiProbeBase = multiProbeSplit[0];
            while((elem=multiProbeSplit.pop()) != null) {
                if(probeBase == multiProbeBase && probeNum == elem) {
                    found = $(e).attr('value');
                }
            }
    }
    });
    return found;
}

$(function() {
    $('#zip').click(function(){
        $(this).attr('href', "/zip/?probes=" + $('select').select2('val'));
    });
});

$(document).ready(function () {
    startRefreshing();

    $('#job-field').numeric({decimal: false, negative: false});

    $('#loading-div-background').css({opacity: 0.75});

    // Init select probe list
    var cookie = $.cookie('probes');
    if(!cookie) {
        var probes = [];
    } else {
        var probes = JSON.parse(cookie);
    }
    $('select').select2({
        placeholder: 'Select probes'
    });
    $('select').select2('val', probes);

    // Event handler for adding a probe
    $(document.body).on('select2-selecting', 'select', function(e) {
        $('.activable').addClass('active');
        var probe = '<a href="/network/probe/' + e.val + '/' + '"><img class="graph" id="' + e.val + '" src="/network/graph/' + e.val + '/1411124629/1411124929/" alt="Graph ' + e.val + '"/></a>';
        $('#probes').append(probe);
        var probes = $('select').select2('val');
        if(jQuery.inArray(e.val, $('select').select2('val')) == -1) {
            probes.push(e.val);
        }
        $('#summary').attr('src', "/network/summary-graph/1411124629/1411124929/?probes=" + probes);
        $('#zip').text('Download selected probes RRD');
        reloadAllImages('last');
    });

    // Event handler for deleting a probe
    $(document.body).on('select2-removing', 'select', function(e) {
        $('.activable').addClass('active');
        $('#' + e.val.replace(/\./g, '\\.')).parent().remove();
        if($('select').select2('val') == '') {
            $('#zip').text('Download all probes RRD');
            $('#summary').attr('src', "/network/summary-graph/1411124629/1411124929/");
        } else {
            $('#zip').text('Download selected probes RRD');
            $('#summary').attr('src', "/network/summary-graph/1411124629/1411124929/?probes=" + $('select').select2('val'));
        }
        reloadAllImages('last');
    });

    // Bind buttons to event handlers
    $('#job-button').click(selectJobId);
    $('#select-all').click(selectAll);
    $('#deselect-all').click(deselectAll);

    // Display the graph for each preselected probes
    $.each(probes, function(index, value) {
        $('select').trigger({
            type: 'select2-selecting',
            val: value
        });
    });


    // Set a cookie storing the probe list
    $(window).unload(function() {
        var value = $('select').val();
        if(value == null) {
            $.removeCookie('probes', {path: '/'});
        } else {
            $.cookie('probes', JSON.stringify(value), {path: '/'});
        }
    });

});
