var smallcaps = /^[A-Z\.0-9]+$/;

var make_word = function(lg, w) {
    let ret = '<div class="word '+lg+'">';
    if (w.footnotes.length || w.notes.length) {
        ret += '<span class="footnote-ref">';
        w.footnotes.forEach(function(f) {
            ret += '['+f+']';
        });
        w.notes.forEach(function(f) {
            ret += '[n'+f+']';
        });
        ret += '</span>';
    }
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
    return ret;
};

var make_inner_line = function(lg, blob, cls) {
    let ret = '<div class="lang-line-inner '+cls+'">';
    blob.words.forEach(function(w) {
        ret += make_word(lg, w);
    });
    ret += '</div>';
    for (let k in blob.trans) {
        ret += '<p class="trans trans-'+lg+'-'+k+'">';
        ret += blob.trans[k];
        ret += '</p>';
    }
    return ret;
};

var make_line = function(lg, blob) {
    if (!blob) {
        return '';
    }
    let ret = '<div class="lang-line '+lg+'">';
    ret += make_inner_line(lg, blob, '');
    ret += '<table><tbody>';
    Object.keys(blob.footnotes).sort().forEach(function(fnid) {
        ret += '<tr><td class="footnote-label"><span>['+fnid+']</span></td><td>';
        ret += make_inner_line(lg, blob.footnotes[fnid], 'footnote');
        ret += '</td></tr>';
    });
    ret += '</tbody></table>';
    ret += '</div>';
    return ret;
};

var make_check = function(lab, cls) {
    return '<input type="checkbox" data-disp="'+cls+'" id="con-'+cls+'" class="lang-control-check"></input><label for="con-'+cls+'">'+lab+'</label>';
};

var make_lang_control = function(lg) {
    let ret = '<div class="lang-control">';
    let lang = LANGS[lg];
    ret += make_check(lang.name, lg);
    ret += '<ol>';
    for (let i = 0; i < lang.lines.length; i++) {
        if (lang.lines[i].type == "morph") {
            for (let j = 0; j < lang.lines[i].labels.length; j++) {
                ret += '<li>';
                ret += make_check(lang.lines[i].labels[j], lg+'-'+i+'-'+j);
                ret += '</li>';
            }
        } else {
            ret += '<li>';
            ret += make_check(lang.lines[i].labels[0], lg+'-'+i);
            ret += '</li>';
        }
    }
    ret += '</ol>';
    ret += '<ul>';
    for (let i = 0; i < lang.trans.length; i++) {
        ret += '<li>';
        ret += make_check(lang.trans[i], 'trans-'+lg+'-'+(i+1));
        ret += '</li>';
    }
    ret += '</ul>';
    ret += '</div>';
    return ret;
};

var show_hide_controls = function() {
    $('#controls').toggle();
};

var show_hide_lines = function() {
    $('.'+$(this).attr('data-disp')).toggle();
};

var setup = function() {
    let con = '';
    LANG_ORDER.forEach(function(lg) {
        con += make_lang_control(lg);
    });
    $('#controls').html(con);
    $('.lang-control-check').click();
    $('.lang-control-check').click(show_hide_lines);
    $('#show-controls').click(show_hide_controls);
    $('#controls').toggle();
    let ret = '';
    TEXT.forEach(function(line) {
        ret += '<div class="line">';
        LANG_ORDER.forEach(function(lg) {
            ret += make_line(lg, line[lg]);
        });
        Object.keys(line.notes).sort().forEach(function(fnid) {
            ret += '<p><span class="footnote-label">[note '+fnid+']</span> '+line.notes[fnid]+'</p>';
        });
        ret += '</div>';
    });
    $('#display').html(ret);
};

setup();

