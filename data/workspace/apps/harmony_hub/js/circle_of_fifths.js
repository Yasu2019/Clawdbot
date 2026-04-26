/**
 * Harmony Hub - Circle of Fifths Logic
 * Provides functions to calculate neighbor keys and relative minor/major.
 */

const CIRCLE_MAJOR = ['C', 'G', 'D', 'A', 'E', 'B', 'Gb', 'Db', 'Ab', 'Eb', 'Bb', 'F'];
const CIRCLE_MINOR = ['Am', 'Em', 'Bm', 'F#m', 'C#m', 'G#m', 'Ebm', 'Bbm', 'Fm', 'Cm', 'Gm', 'Dm'];

/**
 * Get the neighboring keys (left and right) on the Circle of Fifths.
 * @param {string} key - The current key (e.g., 'C' or 'Am')
 * @returns {object} { current, fourth, fifth, relative }
 */
function getNeighbors(key) {
    let index = CIRCLE_MAJOR.indexOf(key);
    let isMinor = false;
    
    if (index === -1) {
        index = CIRCLE_MINOR.indexOf(key);
        isMinor = true;
    }
    
    if (index === -1) return null;
    
    const circle = isMinor ? CIRCLE_MINOR : CIRCLE_MAJOR;
    const relativeCircle = isMinor ? CIRCLE_MAJOR : CIRCLE_MINOR;
    
    const fourth = circle[(index - 1 + 12) % 12];
    const fifth = circle[(index + 1) % 12];
    const relative = relativeCircle[index];
    
    return {
        current: key,
        fourth: fourth,
        fifth: fifth,
        relative: relative,
        isMinor: isMinor
    };
}

// Example usage
if (typeof module !== 'undefined') {
    module.exports = { getNeighbors, CIRCLE_MAJOR, CIRCLE_MINOR };
}