const HERO_INTRO_KEY = 'climber.hero.intro.v1';

let modulePlayed = false;

function readSessionIntro(): boolean {
  try {
    return window.sessionStorage.getItem(HERO_INTRO_KEY) === '1';
  } catch {
    return false;
  }
}

function writeSessionIntro(value: '1' | null): boolean {
  try {
    if (value === null) window.sessionStorage.removeItem(HERO_INTRO_KEY);
    else window.sessionStorage.setItem(HERO_INTRO_KEY, value);
    return true;
  } catch {
    return false;
  }
}

export function hasHeroIntroPlayed(): boolean {
  if (modulePlayed) return true;
  modulePlayed = readSessionIntro();
  return modulePlayed;
}

export function markHeroIntroPlayed(): void {
  modulePlayed = true;
  writeSessionIntro('1');
}

export function resetHeroIntroForTests(): void {
  modulePlayed = false;
  writeSessionIntro(null);
}
