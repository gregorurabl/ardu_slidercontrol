//https://www.benmarshall.me/drupal-behaviors/
//type module
import {
  config_server,
  config_cache,
  config_cache_time,
  config_networks,
  config_max_price,
  config_min_price,
  config_footer_text,
  config_modal_title,
  config_no_results_text
} from './afn_config.js';

//without this, the script will not work on bigpipe pages? like vs node
//https://www.benmarshall.me/drupal-behaviors/
(function ($, Drupal, once) {
  Drupal.behaviors.affSimpleBlock = {
    attach: function (context, settings) {

      /**
       * get aff containerdata and replace data
       * we use data attributes here
       * <div class="aff-data-c aff-main-2 collapsed loading" id="preisvergleich-5" data-ean="4548736112117" data-networks="amazon,ebay,easym,awin" data-cache="true" data-cache-time="60" data-container-class="aff-main-2">
       </div>
       */

//defaults and declare variables /strict)
      let minPrice = config_min_price;
      let maxPrice = config_max_price;
      let ean;
      let network;
      let cache;
      let cache_time;
      let container_class;
      let product_name = false;
      let btns;
      let product_name_;

      //console.log("pvg runs");

//multiple buttons possible
//get values dynamically from data attributes
//if no value avaliable use defaults from config

      //** FOR DRUPAL ****
      //ONLY run the code once on pageload. 'html' is the secret here
      //otherwise you get multiple boxes because of how drupla internally works
      once('loaderboxBehavior', 'html').forEach(function (element) {

        // Get the <span> element that closes the modal
        var afn_container_html = document.querySelectorAll('.attr-loader');

        afn_container_html.forEach(afnc => {
          //console.log("you clicked: " + event.target);

          //MANDATORY MUST EXIST
          ean = afnc.getAttribute('data-ean');

          //if these are not set, use defaults

          //data-product-name
          if (afnc.hasAttribute('data-product-name')) {
            product_name = afnc.getAttribute('data-product-name');
          } else {
            product_name = false;
          }

          //networks
          if (afnc.hasAttribute('data-networks')) {
            network = afnc.getAttribute('data-networks');
          } else {
            network = config_networks;
          }

          //data-cache
          if (afnc.hasAttribute('data-cache')) {
            cache = afnc.getAttribute('data-cache');
          } else {
            cache = config_cache;
          }

          //data-cache-time
          if (afnc.hasAttribute('data-cache-time')) {
            cache_time = afnc.getAttribute('data-cache-time');
          } else {
            cache_time = config_cache_time;
          }

          container_class = '#' + afnc.id;
           // console.log("ean value gotten: " + ean + " from: " + afnc.id);
           // console.log("ean value gotten: " + network + " from: " + afnc.id);
           // console.log("ean value gotten: " + cache + " from: " + afnc.id);
           // console.log("ean value gotten: " + cache_time + " from: " + afnc.id);
           // console.log("ean value gotten: " + container_class + " from: " + afnc.id);

          loadWidget(ean, minPrice = 0, maxPrice = 99999, network, cache, cache_time, container_class, product_name);
        });

        /**
         *
         * @returns {Promise<*>}
         *
         * Lösung? Das script in den header packen!
         * js aggregator (advagg) killt das sript komplett.
         * error: dann gehen auch die js dropdowns des themes nicht mehr etc.
         */
//one or multiple buttons possible
        btns = document.querySelectorAll('.afn-popup');
        //console.log(btns);

//if we have modal buttons we inject modal code
//create the modal dynamically. Only one neccessary because only one visible.
        if (btns) {
          let popup_html = '';
          popup_html = '<div class="aff-main-modal modal" id="preisvergleich-modal">';
          popup_html += '<div class="modal-content">';
          popup_html += '<span class="close-aff">schließen</span>';
          popup_html += '<div class="aff-data aff-main-triggered loading" id="trigger-data">';
          popup_html += '</div>';
          popup_html += '</div>';
          popup_html += '</div>';

          let data_container = document.createElement('div');
          data_container.className = 'afn-popup-container';
          data_container.innerHTML = popup_html;
          document.body.appendChild(data_container);
        }

//the modal container is injected. get it for manipulations
        var modal_trigered = document.getElementById("preisvergleich-modal");

//multiple buttons possible
        btns.forEach(btn => {
          btn.addEventListener('click', function handleClick(event) {

            //console.log("you clicked: " + event.target);
            let ean_ = event.target.getAttribute('data-ean');
            //console.log("ean value clicked: " + ean_);

            if (event.target.hasAttribute('data-product-name')) {
              product_name_ = event.target.getAttribute('data-product-name');
            } else {
              product_name_ = false;
            }
            //console.log("product name: " + product_name_);

            if (ean_ === 0) {
              console.log('error no ean');
            }
            //we have an ean trigger
            else {
              //console.log("ean modal trigger: " + ean);
              modal_trigered.style.display = "block";

              loadWidget(
                ean = ean_, //xm3 4548736112117 //xm5 4548736132580 //ean of product
                minPrice = config_min_price, //optional Standard is 0
                maxPrice = config_max_price, //optional, Standard is 999999
                network = config_networks, //begrenzung der netzwerksuche amazon,ebay oder all für alle
                cache = config_cache, //caching request is necessary to not overload your server!
                cache_time = config_cache_time, //how long should data be cached for the request
                container_class = '.aff-main-triggered',
                product_name = product_name_
              );
            }
          });
        });


// Get the <span> element that closes the modal
//unnötig da jeder close button den modal schließt. es reicht also einer
        var close_button = document.querySelector('.close-aff');
        close_button.addEventListener('click', function handleClick(event) {
          modal_trigered.style.display = "none";
          //remove old content on close. reset
          document.getElementById("trigger-data").innerHTML = "";
          document.getElementById("trigger-data").classList.add("loading");
        });

// When the user clicks anywhere outside of the modal, close it
        document.addEventListener("click", function (event) {
          //console.log("modal click: " + event.target.className);
          if (event.target.classList.contains('aff-main-modal')) {
            modal_trigered.style.display = "none";
            //remove old content on close. reset
            document.getElementById("trigger-data").innerHTML = "";
            document.getElementById("trigger-data").classList.add("loading");
          }
        });

//close alls modals when you press escape
        window.addEventListener('keydown', function (event) {
          if (event.key === 'Escape') {
            modal_trigered.style.display = "none";
            //remove old content on close. reset
            document.getElementById("trigger-data").innerHTML = "";
            document.getElementById("trigger-data").classList.add("loading");
          }
        });

      });

      //end of ONCE


      /**
       * function to call the data server, returnung JSON data
       * @returns {Promise<*>}
       */
      async function getData() {
        //send over params an cache infos
        let url = config_server + '/rest/request/product/filter?op=field&field=ean&ean=' + ean +
          '&filter_unique_ebay=true&min_price=' + minPrice +
          '&max_price=' + maxPrice +
          '&shopIDMode=Include&sort=search_price&category_filter=all&author_brand=&network=' + network +
          '&cache=' + cache +
          '&cache_time=' + cache_time +
          '&product_name=' + product_name +
          '&filter_duplicates=true';

        console.log(url);

        try {
          let res = await fetch(url);
          return await res.json();
        } catch (error) {
          console.log(error);
        }
      }

      /**
       * Render the JSON Data as html
       * @param ean
       * @param minPrice
       * @param maxPrice
       * @param network
       * @param cache
       * @param cache_time
       * @param container_class
       * @param product_name
       * @returns {Promise<void>}
       */
      async function loadWidget(ean, minPrice, maxPrice, network, cache, cache_time, container_class, product_name) {
        let data = await getData(ean, minPrice, maxPrice, network, cache, cache_time, container_class, product_name);
        let html = '';
        let valid_data = false;
        let results = data.length;

        //make this avaliable as config
        let currency = '€';

        //do we have data
        if ((typeof data !== 'undefined') && (data.length > 0)) {
          valid_data = true;
        }

        //beim modal popup setzen wir den text, der ist fest, beim inline kann man den selber festlegen
        if (container_class.indexOf('#') === -1) {
          //console.log("modal exception");
          html += '<h4 class="block-title">' + config_modal_title + '</h4>';
        }

        //#main-container START
        html += '<a class="aff-preisvergleich" name="Preisvergleich"></a>';

        //can be empty in some cases.
        //@todo what if there is no data, empty response?
        //dann preis bei amazon suchen?

        if (valid_data === true) {
          html += '<div class="aff-container">';

          data.forEach(product => {

            html += '<div class="data-row">';

            html += '<div class="shop">';
            html += `<a href="${product.aw_deep_link}" title="Bei ${product.merchant_name} anzeigen" target="_blank"><img loading="lazy" class="shop-logo" src="${product.logo}" alt="shop logo" width="100" height="40"></a>`;
            html += '</div>';

            html += '<div class="preis">';
            html += `<a href="${product.aw_deep_link}" target="_blank" title="Aktuellen Preis abfragen">${product.search_price} ${currency}</a>`;
            html += '</div>';

            html += '<div class="offer-btn">';
            html += `<a href="${product.aw_deep_link}" target="_blank" title="Angebot bei ${product.merchant_name} anzeigen">Zum Angebot</a>`;
            html += '</div>';

            html += '</div>';
          });

          //comntainer 2 end
          html += '</div>';

          html += '<div class="footer">';

          //only show more if more results avaliable
          if (results > 6) {
            html += '<span class="aff-load-all">Mehr Ergebnisse laden</span>';
          }

          html += '<span class="aff-footer">' + config_footer_text + '</span><span class="clearfix"></span></div>'
        }
        //NO RESULTS AT ALL
        else {
          html += '<div class="afn-no-results">' + config_no_results_text + '</div>';
        }

        //#main-container END
        html += '</div>';

        //@todo wie regle ich das jetzt?
        //wenn mehrmals das gleich element, dann einmal replacen und dann copy over? Ausstehend

        //ATTENTION: appendChild only works once, can not replace all containers....
        //use createElement is more performant than direct dom manipulation
        //https://www.javascripttutorial.net/javascript-dom/javascript-createelement/
        //let data_container = document.createElement('div');
        //data_container.className = 'data-container';
        //data_container.innerHTML = html;
        //replace all existing data containers with the data, even if hidden on the page
        let containers = document.querySelectorAll(container_class);
        //console.log(containers);

        containers.forEach((container) => {
          //only replace if it has not already been replaced!
          if (container.querySelector('aff-container') === null) {
            container.innerHTML += html;
            //container.appendChild(data_container);
            //remove the loader class
            container.classList.remove("loading");
          }
        });

        //console.log(data_container);

        //we add the listener to the show more buttons for expand and collapse
        const show_more_btns = document.querySelectorAll(container_class + ' .aff-load-all');
        //console.log("button count: " + show_more_btns.length);

        //because we can have one or multiple
        show_more_btns.forEach(btn => {
          btn.addEventListener('click', event => {
            //console.log("ok1");
            //item.classList.toggle("expanded");
            //console.log(btn.className);
            //console.log(btn);
            //let class_name = btn.className;
            //console.log(btn.parentElement);
            //console.log( btn.parentNode.closest('.aff-data').querySelector('.aff-container'));

            let afn_container = btn.parentNode.closest('.aff-data').querySelector('.aff-container');
            //console.log("container:" + afn_container.classList);
            //console.log(btn.parentNode.closest('.aff-data').id);

            //custom toogle expand/collapse. toggle() not working here...why?
            if (afn_container.classList.contains('expanded')) {
              //console.log("is expanded");
              afn_container.classList.add('collapsed');
              afn_container.classList.remove('expanded');
            } else {
              //console.log("not expanded");
              afn_container.classList.add('expanded');
              afn_container.classList.remove('collapsed');
            }
          });
        });
      }


    }
  };
})(jQuery, Drupal, once);

