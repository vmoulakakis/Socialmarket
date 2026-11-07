import assert from 'node:assert/strict';
import {tokenizeQuery,enrichTerms,inferredBudget,productRelevance,searchShopCatalog} from '../lib/shop-search.mjs';
const products=[
 {id:'1',title:'Luxury LED Ceiling Chandelier for Living Room',sourceCategory:'Indoor Lighting',category:'Φωτισμός',merchant:'AliExpress',price:180,freshness:'recent'},
 {id:'2',title:'OBD2 Automotive Diagnostic Scanner Tool',sourceCategory:'Car Repair Tool',category:'Αυτοκίνητο',merchant:'AliExpress',price:260,freshness:'recent'},
 {id:'3',title:'Γωνιακός καναπές από ύφασμα',sourceCategory:'Σαλόνι',category:'Σπίτι',merchant:'La Redoute',price:550,freshness:'unknown'},
 {id:'4',title:'Small Pendant Lamp Indoor Lighting',sourceCategory:'Indoor Lighting',category:'Φωτισμός',merchant:'AliExpress',price:90,freshness:'aging'},
];
assert.ok(enrichTerms('φωτιστικό οροφής').includes('ceiling'));
assert.ok(enrichTerms('διαγνωστικό εργαλείο αυτοκινήτου').includes('diagnostic'));
assert.equal(inferredBudget('έως 250 ευρώ'),250);
assert.equal(inferredBudget('Θέλω κάτι για το σαλόνι'),null);
assert.ok(productRelevance(products[0],'φωτιστικό οροφής')>productRelevance(products[1],'φωτιστικό οροφής'));
assert.equal(searchShopCatalog(products,{query:'φωτιστικό οροφής'}).results[0].id,'1');
assert.equal(searchShopCatalog(products,{query:'διαγνωστικό αυτοκινήτου'}).results[0].id,'2');
assert.equal(searchShopCatalog(products,{query:'καναπές για μικρό σαλόνι'}).results[0].id,'3');
const under=searchShopCatalog(products,{query:'φωτιστικό',budget:100});
assert.equal(under.total,1);
assert.equal(under.results[0].id,'4');
const greekBudget=searchShopCatalog(products,{query:'φωτιστικό έως 100 ευρώ'});
assert.equal(greekBudget.results[0].id,'4');
assert.equal(searchShopCatalog(products,{category:'Αυτοκίνητο'}).total,1);
assert.equal(searchShopCatalog(products,{category:'Άγνωστη κατηγορία'}).total,0);
assert.equal(searchShopCatalog(products,{query:'φωτιστικό',sort:'price-asc'}).results[0].id,'4');
assert.equal(searchShopCatalog(products,{query:'φωτιστικό',sort:'fresh'}).results[0].id,'1');
assert.equal(searchShopCatalog(products,{query:'φωτιστικό',perPage:1,page:1}).hasMore,true);
assert.equal(searchShopCatalog(products,{query:'φωτιστικό',perPage:1,page:2}).results.length,1);
assert.equal(searchShopCatalog(products,{query:'ανύπαρκτο είδος'}).total,0);
assert.ok(tokenizeQuery('Θέλω ένα φωτιστικό').includes('φωτιστικο'));
assert.ok(!tokenizeQuery('Θέλω ένα φωτιστικό').includes('θελω'));
console.log('SHOP UX data matching, budget, categories, pagination and ranking checks passed.');
