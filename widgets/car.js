// Slot "car" - the car battery flower. Runs INSIDE the phone's Tasker (KW Run, a3) as
// new Function('data', 'slot', 'now', <this>) and must RETURN a Widget v2 layout object.
//   data = body of the slot's "fetch" URL (car-<tok>.txt: "54 Disconnected 1791119700")
//   now  = epoch seconds on the phone
// The BASE placeholder in the two URLs below is replaced by kw_publish.py with the private URL stem.
// The flower itself is a PNG the desktop renders (flower.py via publish.sh);
// only the age is chosen here, because only the phone knows how old the reading is NOW.
// No literal '%' in any text: Tasker would try to read it as a variable.
var raw = (data || '').trim().split(/\s+/);
var at = parseInt(raw[2], 10);
var age = isNaN(at) ? -1 : now - at;
// The age is a SPRITE (age_sprites.py): same square canvas as the flower with only the label drawn
// beside the cable glyph, so the two Fit-scaled Image layers line up at ANY widget size. A Text
// overlay positioned in dp landed in the petals: Tasker never tells us the widget's size.
// Tally marks: each '|' = 10 min, the 5th a slash through four; a full hour becomes a digit and
// the tallies restart ("1 ||" = 1 h 20). t{h}_{n}: h hours 0..23, n tens of minutes 0..5;
// d1..d31 = days (red "3d"); q = no reading.
function label(s) {
  if (s < 0) return 'q';
  if (s < 86400) return 't' + Math.floor(s / 3600) + '_' + Math.floor((s % 3600) / 600);
  return 'd' + Math.min(31, Math.floor(s / 86400));
}
return {
  type: 'Box', fillMaxSize: true, backgroundColor: '#00000000', task: 'KW All',
  contentAlignment: 'Center', useMaterialYouColors: false,
  children: [
    { type: 'Image', url: '__BASE__.png?v=' + (isNaN(at) ? 0 : at) + '-' + now,
      contentScale: 'Fit', size: 'fill' },
    { type: 'Image', url: '__BASE__-age/age-' + label(age) + '.png', contentScale: 'Fit', size: 'fill' }
  ]
};
