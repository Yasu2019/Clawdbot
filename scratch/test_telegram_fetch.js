const fs = require('fs');
async function test() {
  const url = "https://api.telegram.org/bot8085717200:AAHzacN6Q3xSunrLyvUTuHnKEf7Cd5YFdt4/getUpdates";
  const res = await fetch(url);
  const text = await res.text();
  fs.writeFileSync('D:\\Clawdbot_Docker_20260125\\scratch\\updates_test.json', text, 'utf8');
}
test();
