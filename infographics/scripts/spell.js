// macOS system spellchecker via JXA. Usage: osascript -l JavaScript spell.js '["word", ...]'
// Prints a JSON array of the words the system dictionary rejects.
function run(argv) {
  ObjC.import('AppKit');
  var sc = $.NSSpellChecker.sharedSpellChecker;
  var words = JSON.parse(argv[0]);
  var bad = [];
  words.forEach(function (w) {
    var r = sc.checkSpellingOfStringStartingAt(w, 0);
    if (r.length > 0) bad.push(w);
  });
  return JSON.stringify(bad);
}
