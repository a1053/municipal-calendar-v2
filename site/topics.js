/* Clasifica las noticias por tema con palabras clave (sin acentos ni mayúsculas).
 * Funciones puras probadas con Node (tests/topics.test.js). Una noticia puede tener varios temas. */
(function (root) {
  "use strict";

  const TOPICS = [
    { key: "fichajes", label: "Fichajes", re: /\b(fichaj\w*|fichar\w*|ficha a|ficha al|ficho|fichan|fichado\w*|refuerz\w*|contrat(?:a|an|o|ado|ar|acion)\w*|renov\w*|renuev\w*|rescind\w*|traspas\w*|transferenc\w*|prestamo|cedid\w*|mercado de pases|llega(?:ra)? a municipal|nuevo jugador|nuevo delantero|nuevo portero|nuevo defensa|nuevo mediocampista|deja(?:ra)? (?:el club|municipal)|sale de municipal|se va de municipal)\b/ },
    { key: "lesiones", label: "Lesiones", re: /\b(lesion\w*|lesionad\w*|desgarr\w*|esguince|fractur\w*|operacion|operado|recuperacion|recupera(?:rse)?|baja por|molestias|golpe en|rotura|ligamento\w*|cirugia|incapacitad\w*)\b/ },
    { key: "tecnico", label: "Técnico y directiva", re: /\b(tecnico|entrenador|director tecnico|estratega|cuerpo tecnico|directiva|junta directiva|presidente|dirigente\w*|gerente|destituc\w*|destituy\w*|despid\w*|renuncia|conferencia de prensa|asamblea|politica deportiva)\b/ },
    { key: "seleccion", label: "Selección", re: /\b(seleccion|bicolor|convocad\w*|convocatoria|convoca\w*|eliminatoria\w*|sub-?\d\d|premundial|nations league|liga de naciones|amistoso internacional|con la h)\b/ },
  ];

  const norm = (s) => String(s || "").normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase();

  /** Claves de tema de una noticia ({title, summary}). */
  function topicsOf(item) {
    const text = norm(`${(item && item.title) || ""} ${(item && item.summary) || ""}`);
    return TOPICS.filter((t) => t.re.test(text)).map((t) => t.key);
  }

  /** Cuántas noticias hay por tema. */
  function counts(items) {
    const out = {};
    TOPICS.forEach((t) => { out[t.key] = 0; });
    (items || []).forEach((i) => topicsOf(i).forEach((k) => { out[k]++; }));
    return out;
  }

  function filter(items, key) {
    return key && key !== "all" ? (items || []).filter((i) => topicsOf(i).includes(key)) : (items || []);
  }

  const api = { TOPICS: TOPICS.map(({ key, label }) => ({ key, label })), topicsOf, counts, filter };
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  else root.MuniTopics = api;
})(typeof window !== "undefined" ? window : globalThis);
