var smallcaps = /^[A-Z\.0-9]+$/;

var make_line = function(lg, blob) {
    if (!blob) {
        return '';
    }
    let ret = '<div class="lang-line '+lg+'">';
    blob.words.forEach(function(w) {
        ret += '<div class="word '+lg+'">';
        for (let i = 0; i < LANGS[lg].lines.length; i++) {
            let typ = LANGS[lg].lines[i].type;
            let lin = w.lines[i];
            if (!lin) {
                continue;
            }
            if (typ == 'morph') {
                ret += '<table><tbody>';
                for (let j = 0; j < lin.length; j++) {
                    ret += '<tr class="'+lg+'-'+i+'-'+j+'">';
                    ret += lin[j].map(function(m) {
                        if (m.match(smallcaps)) {
                            return '<td class="smallcaps">'+m+'</td>';
                        } else {
                            return '<td>'+m+'</td>';
                        }
                    }).join('');
                    ret += '</tr>';
                }
                ret += '</tbody></table>';
            } else {
                ret += '<p class="'+lg+'-'+i+'">'+lin+'</p>';
            }
        }
        ret += '</div>';
    });
    for (let k in blob.trans) {
        ret += '<p class="trans trans-'+k+'">';
        ret += blob.trans[k];
        ret += '</p>';
    }
    ret += '</div>';
    return ret;
};

var setup = function() {
    let ret = '';
    TEXT.forEach(function(line) {
        ret += '<div class="line">';
        LANG_ORDER.forEach(function(lg) {
            ret += make_line(lg, line[lg]);
        });
        ret += '</div>';
    });
    $('#display').html(ret);
};

setup();
