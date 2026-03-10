// JavaScriptで複数のプルダウンメニューを連動させる方法を現役エンジニアが解説【初心者向け】
// https://magazine.techacademy.jp/magazine/27725

import { Controller } from "@hotwired/stimulus"
export default class extends Controller {
  connect() {
    var select = document.querySelector("#phase");
    //要素がクリックされたら
    //btn.addEventListener('click', function(){
    select.addEventListener('change', function(){
      
      var child_string = document.getElementById("phases"+Number( document.getElementById("phase").value)).value

    Child_JSON.textContent = null;
    //https://www.sejuku.net/blog/79911
    //String排列を、Json排列に変換
    var child_json = JSON.parse(child_string);
    //JavaScriptでselect要素にoptionを追加する方法を現役エンジニアが解説【初心者向け】
    //https://magazine.techacademy.jp/magazine/22315
    child_json.forEach(function(value) {
      var op = document.createElement("option");
      op.value = value.id;
      op.text = value.name;
      Child_JSON.appendChild(op);
    })
    });

    var select = document.querySelector("#Child_JSON");
    select.addEventListener('change', function(){

    var grand_child_string = document.getElementById("phases"+Number( document.getElementById("Child_JSON").value)).value

    Grand_Child_JSON.textContent = null;
    //https://www.sejuku.net/blog/79911
    //String排列を、Json排列に変換  
    var grand_child_json = JSON.parse(grand_child_string);

    //alert (grand_child_string)

    //JavaScriptでselect要素にoptionを追加する方法を現役エンジニアが解説【初心者向け】
    //https://magazine.techacademy.jp/magazine/22315
     grand_child_json.forEach(function(value) {
      var op = document.createElement("option");
      op.value = value.id;
      op.text = value.name;
      Grand_Child_JSON.appendChild(op);
    });
  })
}};

    