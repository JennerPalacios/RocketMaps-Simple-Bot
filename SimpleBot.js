const Discord = require('discord.js');
const bot = new Discord.Client();
const pokemon = require("./files/p-pokemon.json");
const moves = require("./files/p-moves.json");
const token = 'BOT_TOKEN_HERE';

bot.on('ready', () => {
	console.log('-- ROCKETMAP IS READY --');console.log(console.error);
});

// ADD WEBHOOK ID AND TOKEN PER CHANNEL
var discordRareChannel = new Discord.WebhookClient('WEBHOOK_ID_HERE', 'WEBHOOK_TOKEN_HERE');
var discordUnfilteredChannel = new Discord.WebhookClient('WEBHOOK_ID_HERE', 'WEBHOOK_TOKEN_HERE');
	
// EVENT LISTENER
bot.on('message', message => {
	if(!message.content.startsWith('{')) return;	
	
	// SAVE THIS CHANNEL INFO
	var channel = message.channel.name;
	
	// GET ROCKETMAP WEBHOOK OUTPUT FROM ALTERNATE CHANNEL (EXACT NAME)
	if (channel==="rocketmap-webhook") {
		
		// IF CHANNEL NAME IS CORRECT, SAVE ALL TEXT IN A VARIABLE
		var webhook = message.content;
		
		// PARSE VARIABLE AS JSON
		var pokeinfo = JSON.parse(webhook);
	
		// CALC TOTAL SECONDS FROM JSON, CONVERT TO "(X-MINS Y-SECS)"
		var totalsecs = pokeinfo["seconds_until_despawn"];
		var pmins = Math.floor(pokeinfo["seconds_until_despawn"] / 60);
		var psecs = totalsecs - pmins * 60;
		
		// GET CURRENT TIME FOR TIMESTAMP AND TIME "UNTIL" DESPAWN
		var CurrTime = new Date();
		var th = CurrTime.getHours(); if(th>12){th=th-12;}
		timeStamp = th +":"+ CurrTime.getMinutes() +":"+ CurrTime.getSeconds();
		
		// TIME UNTIL DESPAWN, USING CURRENT TIME
		var h = CurrTime.getHours();if(h>12){h=h-12;}if(h<10){h="0"+h;}
		var m = CurrTime.getMinutes()+pmins;if(m>59){m=m-60;h=parseInt(h)+1;}if(m<10){m="0"+m;}
		var s = CurrTime.getSeconds();if(s<10){s="0"+s;}
		var dispawnTime = h + ":" + m + ":" + s;
		
		// CALCULATE TOTAL IV
		let totalIV = ((parseInt(pokeinfo["individual_attack"]) + parseInt(pokeinfo["individual_defense"]) + parseInt(pokeinfo["individual_stamina"])) * 100) / 45;

		// CONVERT ALL DATA INTO SHORT VARIABLES
		let pokeName = pokemon[pokeinfo["pokemon_id"]];
		let pokeAtk = pokeinfo["individual_attack"];
		let pokeDef = pokeinfo["individual_defense"];
		let pokeSta = pokeinfo["individual_stamina"];
		let pokeLat = pokeinfo["latitude"];
		let pokeLng = pokeinfo["longitude"];
		let pokeQuick = moves[pokeinfo["move_1"]];
		let pokeLoad = moves[pokeinfo["move_2"]];
		
		
		// SET DEFAULT COLOR FOR NOTIFICATION (COLOR CODES: https://www.w3schools.com/colors/colors_picker.asp) 
		var colorByIv="#FF0000"; // DEFAULT COLOR: RED (HIGHEST IV)
		if(totalIV<95){colorByIv="#FF7300";}
		if(totalIV<90){colorByIv="#FFFF00";}
		if(totalIV<85){colorByIv="#FFFFFF";}
		if(totalIV<80){colorByIv="#00FF00";}
		
		// SAVE POKEMON ID IN A VARIABLE FOR CUSTOM FILTER
		let pokie = pokeinfo["pokemon_id"];
		
		// ### IV 80+ ###
		// lapras: 131 , snorlax: 143, dratini: 147, dragonair: 148, dragonite: 149,
		// larvitar: 246, pupitar: 247, tyranitar: 248, mareep: 179, flaffy: 180, ampharos: 181, 
		
		// ### IV 0 ###
		// chansey: 113, unown: 201, blisey: 242, porygon: 137
		let SlackMsg = { 
			'username': 'Professor Oak', // NAME OF THE BOT
			'attachments': [{
				'color' : colorByIv,
				'title': pokeName+' '+totalIV.toFixed(0)+'% ('+pokeAtk+'/'+pokeDef+'/'+pokeSta+')', 
				'title_link': 'https://www.google.com/maps/dir//'+pokeLat+','+pokeLng,
				'thumb_url': 'https://raw.githubusercontent.com/kvangent/PokeAlarm/master/icons/'+pokie+'.png',
				'text': pokeQuick+'/'+pokeLoad+'\nUntil '+dispawnTime+' ('+pmins+'m '+psecs+'s)\n\n(`posted at '+timeStamp+'`)'
			}]
		};
		
		// SEND ALL POKEMON TO UNFILTERED FEED
		discordUnfilteredChannel.sendSlackMessage(SlackMsg).catch(console.error);
		
		// CUSTOM FEED FOR CUSTOM CHANNEL
		// ### IV 80+ ###
		// lapras: 131 , snorlax: 143, dratini: 147, dragonair: 148, dragonite: 149, eevee: 133,
		// larvitar: 246, pupitar: 247, tyranitar: 248, mareep: 179, flaffy: 180, ampharos: 181, 
		
		// ### IV 0 ###
		// chansey: 113, unown: 201, blisey: 242, porygon: 137
		if(pokie===131 || pokie===143 || pokie===147 || pokie===148 || pokie===149 || pokie===246 || pokie===247 || pokie===248 || 
			pokie===179 || pokie===180 || pokie===181 || pokie===113 || pokie===201 || pokie===242 || pokie===137 || pokie===133) {
			
			// IF POKEMON MEETS OUR FILTER BY ID, DON'T SEND IT YET:
			let sendit = "no";
			
			// ADD MORE CONDITION, ONLY POKEMONG WITH ID X AND IV 80+, IF X HAS LOWER IV SEND IT TO REGULAR CHANNEL
			if(pokie===131 || pokie===143 || pokie===147 || pokie===148 || pokie===149 || pokie===246 || pokie===247 || 
			pokie===248 || pokie===179 || pokie===180 || pokie===181){
				if( totalIV>80) { 
					sendit="yes"; 
				} 
			}
			// ADD MORE CONDITION, ONLY POKEMON WITH ID X AND IV 0+, AKA UNFILTERED BY IV, BUT FILTERED BY POKEMON ID
			if(pokie===113 || pokie===201 || pokie===242 || pokie===137 || pokie===133) { 
				if(totalIV>0) { 
					sendit="yes";
				}
			}
			
			// IF ID AND IV FILTER SUCCESS, SEND TO CUSTOM FILTERED CHANNEL
			if (sendit==="yes") { 
				return discordRareChannel.sendSlackMessage(SlackMsg).catch(console.error);
			}
		}
	}	
});

// ################################# BOT LOGIN FUNCTION #################################
bot.login(token);

bot.on('disconnected', function () {
		console.log('Disconnected.');console.log(console.error);
		process.exit(1);
});
