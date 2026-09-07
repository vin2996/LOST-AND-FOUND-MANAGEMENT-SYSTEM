function confirmDelete(){return confirm('Delete mo boss? Sure ka?');}
document.addEventListener('DOMContentLoaded',()=>{
  const s=document.getElementById('searchInput');
  if(s){s.addEventListener('input',()=>{
    let v=s.value.toLowerCase();
    document.querySelectorAll('.item-card').forEach(c=>{
      c.parentElement.style.display=c.innerText.toLowerCase().includes(v)?'':'none';
    });
  });}
});