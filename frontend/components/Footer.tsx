import React from 'react';
import { Cpu, Facebook, Instagram, Linkedin, Twitter } from 'lucide-react';

interface FooterProps {
  onNavigateHome: () => void;
}

const Footer: React.FC<FooterProps> = ({ onNavigateHome }) => {
  return (
    <footer className="bg-slate-900 border-t border-slate-800 text-slate-300">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12 lg:py-16">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-8 lg:gap-12">
          
          <div className="col-span-1 md:col-span-1">
            <div className="flex items-center cursor-pointer mb-6 group" onClick={onNavigateHome}>
               <div className="bg-gradient-to-br from-blue-600 to-blue-700 p-2 rounded-lg mr-3 shadow-lg shadow-blue-900/50 group-hover:scale-105 transition-transform">
                  <Cpu className="h-6 w-6 text-white" />
               </div>
               <div>
                 <span className="text-xl font-bold text-white tracking-tight block">Elevex</span>
                 <span className="text-[10px] uppercase tracking-widest text-blue-500 font-semibold">Intelligence</span>
               </div>
            </div>
            <p className="text-slate-400 text-sm leading-relaxed mb-6">
              A inteligência artificial que transforma a manutenção de elevadores. Diagnósticos rápidos, precisos e acessíveis para técnicos modernos.
            </p>
          </div>

          <div>
            <h3 className="text-xs font-bold text-white tracking-widest uppercase mb-6 border-b border-slate-800 pb-2 w-fit">Produto</h3>
            <ul className="space-y-4">
              <li><a href="#features" className="text-slate-400 hover:text-blue-400 transition-colors text-sm hover:translate-x-1 inline-block">Funcionalidades</a></li>
              <li><a href="#audience" className="text-slate-400 hover:text-blue-400 transition-colors text-sm hover:translate-x-1 inline-block">Para Quem</a></li>
              <li><a href="#pricing" className="text-slate-400 hover:text-blue-400 transition-colors text-sm hover:translate-x-1 inline-block">Planos e Preços</a></li>
              <li><a href="#faq" className="text-slate-400 hover:text-blue-400 transition-colors text-sm hover:translate-x-1 inline-block">FAQ</a></li>
            </ul>
          </div>

          <div>
            <h3 className="text-xs font-bold text-white tracking-widest uppercase mb-6 border-b border-slate-800 pb-2 w-fit">Legal</h3>
            <ul className="space-y-4">
              <li><a href="#" className="text-slate-400 hover:text-blue-400 transition-colors text-sm hover:translate-x-1 inline-block">Termos de Uso</a></li>
              <li><a href="#" className="text-slate-400 hover:text-blue-400 transition-colors text-sm hover:translate-x-1 inline-block">Política de Privacidade</a></li>
              <li><a href="#" className="text-slate-400 hover:text-blue-400 transition-colors text-sm hover:translate-x-1 inline-block">Central de Ajuda</a></li>
              <li><a href="#" className="text-slate-400 hover:text-blue-400 transition-colors text-sm hover:translate-x-1 inline-block">Contato</a></li>
            </ul>
          </div>

          <div>
             <h3 className="text-xs font-bold text-white tracking-widest uppercase mb-6 border-b border-slate-800 pb-2 w-fit">Social</h3>
             <p className="text-slate-400 text-sm mb-4">Siga nossas redes e fique por dentro das novidades.</p>
             <div className="flex space-x-4">
               <a href="#" className="bg-slate-800 p-2 rounded-lg text-slate-400 hover:bg-blue-600 hover:text-white transition-all transform hover:-translate-y-1"><Instagram className="w-5 h-5"/></a>
               <a href="#" className="bg-slate-800 p-2 rounded-lg text-slate-400 hover:bg-blue-600 hover:text-white transition-all transform hover:-translate-y-1"><Linkedin className="w-5 h-5"/></a>
               <a href="#" className="bg-slate-800 p-2 rounded-lg text-slate-400 hover:bg-blue-600 hover:text-white transition-all transform hover:-translate-y-1"><Twitter className="w-5 h-5"/></a>
               <a href="#" className="bg-slate-800 p-2 rounded-lg text-slate-400 hover:bg-blue-600 hover:text-white transition-all transform hover:-translate-y-1"><Facebook className="w-5 h-5"/></a>
             </div>
          </div>

        </div>
        
        <div className="mt-16 pt-8 border-t border-slate-800 flex flex-col md:flex-row justify-between items-center gap-4">
          <p className="text-slate-500 text-sm">
            &copy; {new Date().getFullYear()} Elevex Tecnologia Ltda. Todos os direitos reservados.
          </p>
          <div className="flex items-center gap-2 text-xs text-slate-600">
            <span>Segurança</span>
            <span className="w-1 h-1 bg-slate-600 rounded-full"></span>
            <span>Privacidade</span>
            <span className="w-1 h-1 bg-slate-600 rounded-full"></span>
            <span>Compliance</span>
          </div>
        </div>
      </div>
    </footer>
  );
};

export default Footer;