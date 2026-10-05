// Any slot with no widgets/<slot>.js yet. It must NOT reach KW Run's Widget v2 action: Widget v2
// on a name that isn't on the home screen pops Android's "add widget?" pin request (one per free
// slot on every hourly run). Throwing fails the JavaScriptlet, which stops KW Run before a4. The
// marker text lets kw_publish.py's self-test tell this from a real bug.
throw new Error('KW_FREE_SLOT ' + slot);
