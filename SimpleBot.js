const Discord = require('discord.js');
const bot = new Discord.Client();
const pokemon = require("./files/p-pokemon.json");
const moves = require("./files/p-moves.json");
const token = 'MjgzNjUzOTk1Nzg2OTI4MTI5.C44M4w.iOVZHG85sGwptnYshOIkKaYFnDY';


bot.on('ready', () => {
	console.log('-- Seattle BOT IS READY --');console.log(console.error);
});


// ADD WEBHOOK ID AND TOKEN PER CHANNEL
var dragonite_channel = new Discord.WebhookClient('WEBHOOK_ID_HERE', 'WEBHOOK_TOKEN_HERE');

// NAMES OF THE ACTUAL CHANNEL IN DISCORD
var discord_chan_input = "rocketmap-webhook";
var discord_chan_dragonite = "dragonites";

// EVENT LISTENER
bot.on('message', message => {
	
	// SAVE CHANNEL INFO PER CHANNEL
	var channel = message.channel.name;
	
	// GET ROCKETMAP OUTPUT INFORMATION
	if (channel===discord_chan_input) {
		
		// SAVE ALL TEXT IN A VARIABLE
		var webhook = message.content;
		
		// PARSE VARIABLE AS JSON
		var pokeinfo = JSON.parse(webhook);
	
		// CALCULATE TOTAL SECONDS INTO "X-MINS Y-SECS" LEFT
		var totalsecs = pokeinfo["seconds_until_despawn"];
		var pmins = Math.floor(pokeinfo["seconds_until_despawn"] / 60);
		var psecs = totalsecs - pmins * 60;
		
		// GET CURRENT TIME FOR TIMESTAMP AND TIME "UNTIL DISAPPEAR"
		var CurrTime = new Date();
		var th = CurrTime.getHours(); if(th>12){th=(th)-(12);}
		timeStamp = th +":"+ CurrTime.getMinutes() +":"+ CurrTime.getSeconds();
		
		// TIME UNTIL DESPAWN
		var h = CurrTime.getHours();if(h>12){h=h-12;}if(h<10){h="0"+h;}
		var m = CurrTime.getMinutes()+pmins;if(m>59){m=m-60;h=parseInt(h)+(1);}if(m<10){m="0"+m;}
		var s = CurrTime.getSeconds();if(s<10){s="0"+s;}
		var outTime = h + ":" + m + ":" + s;
		
		// CALCULATE OVERALL IV
		let totalIV = ((parseInt(pokeinfo["individual_attack"]) + parseInt(pokeinfo["individual_defense"]) + parseInt(pokeinfo["individual_stamina"])) * 100) / 45;
		
		// SET DEFAULT COLOR FOR NOTIFICATION (COLOR CODES: https://www.w3schools.com/colors/colors_picker.asp) 
		var slacol="#FF0000";
		if(totalIV<90){slacol="#E61A00";}
		if(totalIV<80){slacol="#BF4000";}
		if(totalIV<70){slacol="#996600";}
		if(totalIV<60){slacol="#738C00";}
		if(totalIV<50){slacol="#4DB200";}
		if(totalIV<40){slacol="#26D900";}
		if(totalIV<30){slacol="#00FF00";}
		
		// SEND NOTIFICATION TO CHANNELS
		discord_chan_dragonite.sendSlackMessage({
			'username': 'Professor Oak',
			'attachments': [{
				'color' : slacol,
				'title': '['+pokeinfo["pokemon_id"]+'] '+pokemon[pokeinfo["pokemon_id"]]+' '+totalIV.toFixed(0)+'% ('
					+pokeinfo["individual_attack"]+'/'+pokeinfo["individual_defense"]+'/'+pokeinfo["individual_stamina"]+')', 
				'title_link': 'https://www.google.com/maps/dir//'+pokeinfo["latitude"]+','+pokeinfo["longitude"],
				'thumb_url': 'https://raw.githubusercontent.com/kvangent/PokeAlarm/master/icons/'+pokeinfo["pokemon_id"]+'.png',
				'text': moves[pokeinfo["move_1"]]+'/'+moves[pokeinfo["move_2"]]+'\nUntil '+outTime+' ('+pmins+'m '+psecs+'s)\n\n`posted at '+timeStamp+'`'
			}]
		}).catch(console.error);
		
	}	
});

// log our bot in
bot.login(token);

bot.on('disconnected', function () {
		console.log('Disconnected.');console.log(console.error);
		process.exit(1);
});