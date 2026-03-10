const fs = require('fs');
const bcrypt = require('bcryptjs');
const dotenv = require('dotenv');
const path = require('path');

dotenv.config();

const settings = {
  adminAuth: {
    type: "credentials",
    users: [{
      username: process.env.NODERED_USERNAME,
      password: bcrypt.hashSync(process.env.NODERED_PASSWORD, 8),
      permissions: "*"
    }]
  }
};

fs.writeFileSync('/usr/src/nodered/settings.js', 'module.exports = ' + JSON.stringify(settings));