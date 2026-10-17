// public domain paintings, bundled so the page works offline. add one by dropping a 640px jpg in art/ and a line here.
// the optional last field is where the 4:3 plate crops a tall painting, so the subject stays in frame
export const PAINTINGS = [
  ["grande-jatte", "Georges Seurat", "A Sunday on La Grande Jatte", "1884–86"],
  ["sunrise", "Claude Monet", "Impression, Sunrise", "1872"],
  ["cypresses", "Vincent van Gogh", "Wheat Field with Cypresses", "1889"],
  ["delft", "Johannes Vermeer", "View of Delft", "c. 1660"],
  ["water-lilies", "Claude Monet", "Water Lilies", "1906"],
  ["starry-night", "Vincent van Gogh", "The Starry Night", "1889"],
  ["magpie", "Claude Monet", "The Magpie", "1869"],
  ["parasol", "Claude Monet", "Woman with a Parasol", "1875", "50% 18%"],
  ["poppies", "Claude Monet", "Poppy Field", "1873"],
  ["bridge", "Claude Monet", "Bridge over a Pond of Water Lilies", "1899"],
  ["haystacks", "Claude Monet", "Haystacks, End of Summer", "1891"],
  ["cafe", "Vincent van Gogh", "Café Terrace at Night", "1888", "50% 40%"],
  ["irises", "Vincent van Gogh", "Irises", "1889"],
  ["almond", "Vincent van Gogh", "Almond Blossom", "1890"],
  ["bedroom", "Vincent van Gogh", "The Bedroom", "1889"],
  ["bathers", "Georges Seurat", "Bathers at Asnières", "1884"],
  ["milkmaid", "Johannes Vermeer", "The Milkmaid", "c. 1658", "50% 30%"],
  ["wave", "Katsushika Hokusai", "The Great Wave off Kanagawa", "c. 1831"],
  ["temeraire", "J. M. W. Turner", "The Fighting Temeraire", "1839"],
  ["victoire", "Paul Cézanne", "Mont Sainte-Victoire", "c. 1887"],
  ["rainyday", "Gustave Caillebotte", "Paris Street; Rainy Day", "1877"],
  ["galette", "Pierre-Auguste Renoir", "Dance at Le Moulin de la Galette", "1876"],
  ["shower", "Utagawa Hiroshige", "Sudden Shower over Shin-Ōhashi Bridge", "1857"],
];

// a new painting on every new tab. it deals from a shuffled deck kept in localStorage, so every painting
// shows once before any repeats, and the last one of a deck never opens the next
const KEY = 'shelf:paintings';

function shuffle(a) {
  for (let i = a.length - 1; i > 0; i--) { const j = Math.floor(Math.random() * (i + 1)); [a[i], a[j]] = [a[j], a[i]]; }
  return a;
}

export function next() {
  let st;
  try { st = JSON.parse(localStorage.getItem(KEY)) || {}; } catch { st = {}; }
  const keys = PAINTINGS.map(p => p[0]);
  let deck = (st.deck || []).filter(k => keys.includes(k));
  if (!deck.length) {
    deck = shuffle([...keys]);
    if (deck[0] === st.last && deck.length > 1) deck.push(deck.shift());
  }
  const k = deck.shift();
  localStorage.setItem(KEY, JSON.stringify({ deck, last: k }));
  const [key, artist, title, year, focus = '50% 50%'] = PAINTINGS.find(p => p[0] === k);
  return { src: `art/${key}.jpg`, key, artist, title, year, focus };
}
