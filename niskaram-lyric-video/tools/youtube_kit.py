#!/usr/bin/env python3
"""Writes the YouTube launch kit into youtube/:
     description_main.txt      paste-ready description (chapters from the caption SRT + the user's lyrics, verbatim)
     tags.txt                  tag list (<= 500 characters)
     titles.txt                title options (<= 100 characters each)
     niskaram_captions_english_DRAFT.srt   English subtitle draft on the same cue times
     YouTube_Upload_Kit.md     the full plan (titles, settings, Shorts/Reels copy, schedule)
Lyrics come from inputs/lyrics.srt, cue times from youtube/niskaram_captions_malayalam.srt, so nothing is retyped by hand.
"""
import pathlib, re, sys
ROOT = pathlib.Path(__file__).resolve().parent.parent
YT = ROOT / 'youtube'

def read_srt(path):
    cues = []
    for blk in path.read_text(encoding='utf8').strip().split('\n\n'):
        L = blk.split('\n')
        a, b = L[1].split(' --> ')
        cues.append({'n': int(L[0]), 't0': sec(a), 't1': sec(b), 'text': '\n'.join(L[2:])})
    return cues

def sec(t):
    h, m, r = t.split(':'); s, ms = r.split(',')
    return int(h) * 3600 + int(m) * 60 + int(s) + int(ms) / 1000

def stamp(t):
    return f'{int(t // 60)}:{int(t % 60):02d}'

def srt_time(t):
    ms = round(t * 1000); h, ms = divmod(ms, 3600000); m, ms = divmod(ms, 60000); s, ms = divmod(ms, 1000)
    return f'{h:02d}:{m:02d}:{s:02d},{ms:03d}'

lyrics = [c['text'] for c in read_srt(ROOT / 'inputs' / 'lyrics.srt')]
cues = read_srt(YT / 'niskaram_captions_malayalam.srt')
assert [c['text'] for c in cues] == lyrics and len(lyrics) == 55, 'caption SRT must carry the lyrics verbatim'

# ------------------------------------------------------------------ chapters (first at 0:00, each >= 10 s, at least 3)
FIXED = [(0.0, 'ആദാൻ · The Call to Prayer (Intro)'), (11.0, 'നിസ്കാരം · Title')]
BY_CUE = [(1, 'ദുനിയാവിൻ മോഹങ്ങൾ മാഞ്ഞുപോകും'), (3, 'ഖബറിലെ ആദ്യത്തെ ചോദ്യം വരും'), (7, 'അഞ്ചു നേരം പള്ളിയിൽ നിന്നും'),
          (11, 'പാപങ്ങൾ മായ്ക്കുന്ന പുണ്യം'), (13, 'ഹൃദയത്തിൻ നോവുകൾ · സുജൂദ്'), (17, 'ഖബറിലെ ആദ്യത്തെ ചോദ്യം'),
          (19, 'നിസ്കാരം വേണ്ടെന്ന് വെച്ചവർ'), (21, 'വിചാരണ നേരം'), (25, 'ജീവൻ തൊണ്ടയിൽ എത്തുന്നേരം'),
          (31, 'വുദു · ശുദ്ധിയിൽ പായ വിരിച്ച്'), (37, 'സ്വർഗ്ഗത്തിൻ പൂങ്കാവനം'), (39, 'നിസ്കാര വഴിയിൽ ഉറച്ചുനിന്നാൽ'),
          (41, 'യാ റബ്ബേ…'), (45, 'ദുനിയാവിൻ മോഹങ്ങൾ (final)'), (51, 'ഖബറിലെ ആദ്യത്തെ ചോദ്യം (final)'),
          (53, 'നിസ്കാര വഴി · ഇരുലോക വിജയം'), (55, 'യാ റബ്ബേ… (Outro)')]
chap = FIXED + [(int(cues[n - 1]['t0']), label) for n, label in BY_CUE]
for (a, _), (b, _) in zip(chap, chap[1:]):
    assert b - a >= 10, f'chapters closer than 10 s: {stamp(a)} -> {stamp(b)}'
chapters = '\n'.join(f'{stamp(t)} {label}' for t, label in chap)

# ------------------------------------------------------------------ description
DESC = '''“ഖബറിലെ ആദ്യത്തെ ചോദ്യം വരും, നിസ്കരിച്ചോയെന്ന് റബ്ബ് ചോദിക്കും!” 🤲
നിസ്കാരം | Niskaram — നിസ്കാരത്തെ ഓർമ്മിപ്പിക്കുന്ന, ഹൃദയത്തെ തൊടുന്ന ഒരു മലയാളം ഇസ്ലാമിക ഗാനം (Official Lyric Video).

#Niskaram #MalayalamIslamicSong #MirayaStudio #HayyaAlasSalah #Namaz

Niskaram (നിസ്കാരം) is a new Malayalam Islamic song about salah (the five daily prayers): a reminder for the heart. The desires of this world fade, the grave is a lonely place, and the song asks: "Did you pray?" Title calligraphy: حَيَّ عَلَى الصَّلَاةِ (Hayya 'alas-salah — "Come to prayer"). English subtitles are available: turn on CC.

ഈ പാട്ട് ഹൃദയത്തിൽ തൊട്ടെങ്കിൽ 👍 ലൈക്ക് ചെയ്യൂ, കമന്റ് ചെയ്യൂ, നിസ്കരിക്കാൻ മറന്നുപോകുന്ന ഒരാൾക്കെങ്കിലും ഷെയർ ചെയ്യൂ. 🔔 Miraya Studio ചാനൽ സബ്സ്ക്രൈബ് ചെയ്യൂ — പുതിയ പാട്ടുകൾ ആദ്യം കേൾക്കാം.

⏱ CHAPTERS
{CHAPTERS}

🎼 CREDITS
Music: Miraya Studio
Lyrics: Jabir Varikkodan
Editor: Jabir Varikkodan
Mixing & Visuals: Miraya Studio
Stock footage: Mixkit (mixkit.co)

📜 വരികൾ / LYRICS
{LYRICS}

ഹയ്യ അലസ്സ്വലാഹ് · Hayya 'alas-salah · A Reflection for the Heart
© Miraya Studio'''
# the lyric block keeps the song's own blank-line-free layout, one verse (4 lines) per paragraph
verses, cur = [], []
for i, l in enumerate(lyrics, 1):
    cur.append(l)
    if i % 4 == 0 or i == len(lyrics):
        verses.append('\n'.join(cur)); cur = []
desc = DESC.replace('{CHAPTERS}', chapters).replace('{LYRICS}', '\n\n'.join(verses))
assert '<' not in desc and '>' not in desc, 'YouTube rejects < and > in descriptions'
assert len(desc) <= 5000, len(desc)
(YT / 'description_main.txt').write_text(desc + '\n', encoding='utf8')
# fallback without the lyric block: the Data API documents the description limit as 5000 BYTES (Malayalam = 3 bytes/char);
# if Studio refuses the full text, this version always fits
short = DESC.replace('📜 വരികൾ / LYRICS\n{LYRICS}\n\n', '').replace('{CHAPTERS}', chapters)
assert len(short.encode('utf8')) <= 5000, len(short.encode('utf8'))
(YT / 'description_short_no_lyrics.txt').write_text(short + '\n', encoding='utf8')

# ------------------------------------------------------------------ titles and tags
TITLES = [
    ('T1 · search-first (brand + keywords)', 'നിസ്കാരം | Niskaram – Malayalam Islamic Song | Official Lyric Video | Miraya Studio'),
    ('T2 · hook-first (recommended with thumbnail A)', 'ഖബറിലെ ആദ്യത്തെ ചോദ്യം… നിസ്കരിച്ചോ? | Niskaram – Malayalam Islamic Song | Miraya Studio'),
    ('T3 · English-reader friendly', 'Niskaram (നിസ്കാരം) – New Malayalam Islamic Song | Hayya Alas Salah | Lyric Video'),
]
for _, t in TITLES:
    assert len(t) <= 100 and '<' not in t and '>' not in t, (len(t), t)
(YT / 'titles.txt').write_text('\n'.join(t for _, t in TITLES) + '\n', encoding='utf8')

TAGS = ['niskaram', 'നിസ്കാരം', 'niskaram malayalam song', 'malayalam islamic song', 'new malayalam islamic song',
        'malayalam nasheed', 'islamic song malayalam', 'namaz song malayalam', 'salah song malayalam', 'hayya alas salah',
        'ഖബറിലെ ആദ്യത്തെ ചോദ്യം', 'ഇസ്ലാമിക ഗാനം', 'malayalam lyric video', 'islamic lyric video', 'miraya studio',
        'jabir varikkodan', 'sujood', 'malayalam islamic reminder', 'kerala islamic song', 'niskarm', 'niskaaram']
tagline = ','.join(TAGS)
assert len(tagline) <= 500, len(tagline)
(YT / 'tags.txt').write_text(tagline + '\n', encoding='utf8')

# ------------------------------------------------------------------ English subtitle draft (same cue times)
EN = {1: 'The desires of this world will fade away,', 2: 'and you will be alone inside the grave…',
      3: 'The first question in the grave will come,', 4: '"Did you pray?" your Lord will ask!',
      7: 'Five times a day, from the mosque,', 8: 'when you hear the call "Allahu Akbar",',
      9: 'do not lie there in laziness,', 10: 'life will run out — do not forget!',
      11: 'It is a virtue that washes sins away,', 12: 'it is a duty owed to the Creator…',
      13: 'To heal the pains of the heart,', 14: 'there is no medicine greater than sujood, my friend!',
      19: 'Those who gave up prayer —', 20: 'have they not thrown themselves into the fire of Hell…',
      21: 'On the Day to come, at the time of reckoning,', 22: 'what use is shedding tears then?',
      23: "In the Lord's court, what will you say?", 24: 'Will standing there empty-handed save you?',
      25: 'When the soul reaches the throat,', 26: 'what use is weeping in regret?',
      31: 'In the purity of wudu, spreading out the prayer mat,', 32: 'as you stand before your Master…',
      33: 'filling the heart with flowers of humility,', 34: 'performing the prayer with khushu’ (a humble, focused heart)…',
      35: 'in supplications mixed with tears,', 36: 'seek the mercy of your Lord…',
      37: 'The hope of the flower-garden of Paradise', 38: 'is the prayer — do not forget it…',
      39: 'If you stay firm on the path of prayer,', 40: 'you will attain success in both worlds…',
      41: 'O my Lord… O my Lord…', 42: 'O my Lord… O my Lord…',
      43: 'Lay your forehead down in sujood…', 44: 'seek the mercy of your Lord…',
      53: 'If you stay firm on the path of prayer,', 54: 'you will attain success in both worlds…', 55: 'O my Lord… O my Lord…'}
# a repeated line (chorus, final refrain) takes the translation of its first occurrence
first = {}
for n, text in enumerate(lyrics, 1): first.setdefault(text, n)
EN = {n: EN[first[text]] for n, text in enumerate(lyrics, 1)}
missing = [c['n'] for c in cues if c['n'] not in EN]
assert not missing, missing
(YT / 'niskaram_captions_english_DRAFT.srt').write_text(
    '\n\n'.join(f"{c['n']}\n{srt_time(c['t0'])} --> {srt_time(c['t1'])}\n{EN[c['n']]}" for c in cues) + '\n', encoding='utf8')

# ------------------------------------------------------------------ the kit
KIT = (ROOT / 'tools' / 'youtube_kit_template.md').read_text(encoding='utf8')
titles_md = '\n'.join(f'{i}. **{lbl}**  \n   `{t}`  \n   ({len(t)} അക്ഷരം)' for i, (lbl, t) in enumerate(TITLES, 1))
kit = (KIT.replace('{TITLES}', titles_md).replace('{TAGS}', tagline).replace('{TAGCOUNT}', str(len(tagline)))
          .replace('{DESCRIPTION}', desc).replace('{DESCCOUNT}', str(len(desc))).replace('{CHAPTERS}', chapters))
(YT / 'YouTube_Upload_Kit.md').write_text(kit, encoding='utf8')
print('description', len(desc), 'chars,', len(desc.encode('utf8')), 'bytes | short', len(short.encode('utf8')), 'bytes | tags', len(tagline), 'chars | titles', [len(t) for _, t in TITLES], '| chapters', len(chap))
