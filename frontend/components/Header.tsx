import React, { useState, useEffect } from 'react';
import { Cpu, Menu, X, ChevronRight, LogIn, UserPlus } from 'lucide-react';

interface HeaderProps {
  currentView?: 'landing' | 'app';
  onNavigateHome?: () => void;
  onNavigateApp?: () => void;
  onLogin?: () => void;
}

const Header: React.FC<HeaderProps> = ({ currentView = 'landing', onNavigateHome, onNavigateApp, onLogin }) => {
  const [isMenuOpen, setIsMenuOpen] = useState(false);
  const [scrolled, setScrolled] = useState(false);

  useEffect(() => {
    const handleScroll = () => setScrolled(window.scrollY > 20);
    window.addEventListener('scroll', handleScroll);
    return () => window.removeEventListener('scroll', handleScroll);
  }, []);

  const navLinkClass = "text-sm font-medium text-slate-600 hover:text-blue-600 transition-colors relative group py-2";
  const mobileLinkClass = "block px-4 py-3 text-base font-medium text-slate-600 hover:text-blue-600 hover:bg-slate-50 rounded-lg transition-all";

  return (
    <header 
      className={`fixed top-0 w-full z-50 transition-all duration-300 border-b ${
        scrolled 
          ? 'bg-white/95 backdrop-blur-md border-slate-200 shadow-sm py-3' 
          : 'bg-white/50 backdrop-blur-sm border-transparent py-5'
      }`}
    >
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between items-center">
          {/* Logo */}
          <div className="flex items-center cursor-pointer group" onClick={onNavigateHome}>
            <div className="bg-gradient-to-br from-blue-600 to-blue-700 p-2.5 rounded-xl mr-3 shadow-lg shadow-blue-500/20 group-hover:shadow-blue-500/30 transition-all transform group-hover:-translate-y-0.5">
              <Cpu className="h-6 w-6 text-white" />
            </div>
            <div>
              <span className="text-xl font-bold text-slate-900 tracking-tight block leading-none">Elevex</span>
              <span className="text-[10px] font-semibold text-blue-600 tracking-wider uppercase">Intelligence</span>
            </div>
          </div>

          {/* Desktop Nav */}
          <nav className="hidden md:flex items-center space-x-8">
            {currentView === 'landing' && (
              <div className="flex items-center space-x-8 bg-white/50 px-6 py-2 rounded-full border border-slate-100 backdrop-blur-sm shadow-sm">
                <a href="#" onClick={(e) => { e.preventDefault(); window.scrollTo({ top: 0, behavior: 'smooth' }); }} className={navLinkClass}>Início</a>
                <a href="#features" className={navLinkClass}>O que é</a>
                <a href="#audience" className={navLinkClass}>Para quem</a>
                <a href="#pricing" className={navLinkClass}>Planos</a>
                <a href="#faq" className={navLinkClass}>FAQ</a>
              </div>
            )}
          </nav>

          {/* Actions */}
          <div className="hidden md:flex items-center space-x-3">
            {currentView === 'landing' ? (
              <>
                <button
                  onClick={onLogin}
                  className="px-5 py-2.5 rounded-xl font-semibold text-sm transition-all text-slate-600 hover:text-blue-600 hover:bg-blue-50 flex items-center gap-2"
                >
                  <LogIn size={18} />
                  Entrar
                </button>
                <button
                  onClick={onNavigateApp}
                  className="px-5 py-2.5 rounded-xl font-semibold text-sm transition-all shadow-lg shadow-blue-500/25 hover:shadow-blue-500/40 bg-blue-600 text-white hover:bg-blue-700 transform hover:-translate-y-0.5 flex items-center gap-2"
                >
                  <UserPlus size={18} />
                  Criar Conta
                </button>
              </>
            ) : (
              <button
                onClick={onNavigateHome}
                className="px-5 py-2.5 rounded-xl font-semibold text-sm transition-all shadow-sm hover:shadow bg-white border border-slate-200 text-slate-700 hover:border-slate-300 flex items-center gap-2"
              >
                <ChevronRight size={16} className="rotate-180" />
                Voltar ao Início
              </button>
            )}
          </div>

          {/* Mobile Menu Button */}
          <div className="md:hidden flex items-center">
            <button
              onClick={() => setIsMenuOpen(!isMenuOpen)}
              className="p-2 text-slate-600 hover:text-blue-600 hover:bg-slate-100 rounded-lg transition-colors focus:outline-none"
              aria-label="Abrir menu"
            >
              {isMenuOpen ? <X className="h-6 w-6" /> : <Menu className="h-6 w-6" />}
            </button>
          </div>
        </div>
      </div>

      {/* Mobile Menu Overlay */}
      <div 
        className={`md:hidden fixed inset-0 z-40 bg-white transform transition-transform duration-300 ease-in-out ${
          isMenuOpen ? 'translate-x-0' : 'translate-x-full'
        }`}
        style={{ top: '70px' }}
      >
        <div className="p-4 space-y-2 h-full overflow-y-auto pb-20">
           {currentView === 'landing' && (
            <div className="space-y-1 mb-8">
              <h3 className="px-4 text-xs font-bold text-slate-400 uppercase tracking-wider mb-2">Navegação</h3>
              <a onClick={() => setIsMenuOpen(false)} href="#" className={mobileLinkClass}>Início</a>
              <a onClick={() => setIsMenuOpen(false)} href="#features" className={mobileLinkClass}>Funcionalidades</a>
              <a onClick={() => setIsMenuOpen(false)} href="#audience" className={mobileLinkClass}>Para Quem</a>
              <a onClick={() => setIsMenuOpen(false)} href="#pricing" className={mobileLinkClass}>Planos e Preços</a>
              <a onClick={() => setIsMenuOpen(false)} href="#faq" className={mobileLinkClass}>Perguntas Frequentes</a>
            </div>
           )}

            <div className="border-t border-slate-100 pt-6 space-y-3 px-4">
              {currentView === 'landing' ? (
                <>
                  <button
                    onClick={() => { onLogin?.(); setIsMenuOpen(false); }}
                    className="w-full flex items-center justify-center gap-2 px-4 py-3.5 rounded-xl text-base font-semibold text-slate-700 bg-slate-50 border border-slate-200 active:scale-[0.98] transition-transform"
                  >
                    <LogIn size={20} />
                    Acessar Conta
                  </button>
                  <button
                    onClick={() => { onNavigateApp?.(); setIsMenuOpen(false); }}
                    className="w-full flex items-center justify-center gap-2 px-4 py-3.5 rounded-xl text-base font-bold text-white bg-blue-600 shadow-lg shadow-blue-500/20 active:scale-[0.98] transition-transform"
                  >
                    <UserPlus size={20} />
                    Começar Gratuitamente
                  </button>
                </>
              ) : (
                <button
                  onClick={() => { onNavigateHome?.(); setIsMenuOpen(false); }}
                  className="w-full flex items-center justify-center gap-2 px-4 py-3.5 rounded-xl text-base font-bold text-blue-600 bg-blue-50 active:scale-[0.98]"
                >
                  <ChevronRight size={20} className="rotate-180" />
                  Voltar ao Início
                </button>
              )}
            </div>
        </div>
      </div>
    </header>
  );
};

export default Header;