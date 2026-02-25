
import React, { useState, useEffect } from 'react';
import { Handshake, ShieldCheck, User, Lock, ArrowRight, Cpu, ArrowLeft } from 'lucide-react';
import * as Storage from '../services/storage';

interface AuthProps {
  onLoginSuccess: () => void;
  onBack: () => void;
}

const Auth: React.FC<AuthProps> = ({ onLoginSuccess, onBack }) => {
  const [role, setRole] = useState<'user' | 'admin'>('user');
  const [isLoading, setIsLoading] = useState(false);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');

  // Auto-fill demo credentials
  useEffect(() => {
    if (role === 'admin') {
      setEmail('admin@elevex.com');
      setPassword('admin123');
    } else {
      setEmail('carlos@tecnico.com');
      setPassword('123456');
    }
  }, [role]);

  const handleLogin = (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    
    // Simulating API Call
    setTimeout(() => {
        Storage.login(role);
        setIsLoading(false);
        onLoginSuccess();
    }, 800);
  };

  return (
    <div className="min-h-screen bg-slate-50 flex flex-col relative overflow-hidden">
      {/* Background decoration */}
      <div className="absolute top-0 left-0 w-full h-full overflow-hidden z-0 pointer-events-none">
          <div className="absolute -top-[20%] -left-[10%] w-[60%] h-[60%] bg-blue-600/5 rounded-full blur-[100px]"></div>
          <div className="absolute -bottom-[20%] -right-[10%] w-[60%] h-[60%] bg-cyan-500/5 rounded-full blur-[100px]"></div>
      </div>

      {/* Header */}
      <header className="relative z-10 border-b border-slate-200 bg-white/80 backdrop-blur-md">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center h-16">
            <div className="flex items-center cursor-pointer group" onClick={onBack}>
              <div className="bg-gradient-to-br from-blue-600 to-blue-700 p-2 rounded-lg mr-2 shadow-md shadow-blue-500/20 group-hover:shadow-blue-500/30 transition-all">
                <Cpu className="h-5 w-5 text-white" />
              </div>
              <span className="text-lg font-bold text-slate-900 tracking-tight">Elevex</span>
            </div>
            <button 
              onClick={onBack} 
              className="text-slate-500 hover:text-blue-600 text-sm font-medium flex items-center gap-1.5 transition-colors bg-slate-100 hover:bg-blue-50 px-3 py-1.5 rounded-full"
            >
              <ArrowLeft size={16} /> Voltar
            </button>
          </div>
        </div>
      </header>

      {/* Content */}
      <div className="flex-1 flex items-center justify-center p-4 relative z-10">
      <div className="w-full max-w-md bg-white rounded-3xl shadow-xl border border-slate-200/60 overflow-hidden animate-fade-in">
        <div className="p-8 text-center bg-white border-b border-slate-100">
             <div className="flex justify-center mb-5">
                 <div className="bg-blue-50 p-4 rounded-2xl shadow-inner border border-blue-100">
                <Handshake className="h-8 w-8 text-blue-600" />
                 </div>
             </div>
             <h2 className="text-2xl font-extrabold text-slate-900 tracking-tight">Bem-vindo de volta</h2>
             <p className="text-slate-500 mt-2 text-sm">Acesse sua central de inteligência técnica</p>
        </div>

        {/* Role Toggles */}
        <div className="flex border-b border-slate-100 bg-slate-50/50 p-1.5 gap-1 mx-6 mt-6 rounded-xl">
            <button 
                onClick={() => setRole('user')}
                className={`flex-1 py-2.5 text-sm font-semibold flex items-center justify-center gap-2 transition-all rounded-lg ${role === 'user' ? 'text-blue-700 bg-white shadow-sm border border-slate-200/50' : 'text-slate-500 hover:text-slate-700 hover:bg-slate-100'}`}
            >
                <User size={16} />
                Técnico
            </button>
            <button 
                onClick={() => setRole('admin')}
                className={`flex-1 py-2.5 text-sm font-semibold flex items-center justify-center gap-2 transition-all rounded-lg ${role === 'admin' ? 'text-blue-700 bg-white shadow-sm border border-slate-200/50' : 'text-slate-500 hover:text-slate-700 hover:bg-slate-100'}`}
            >
                <ShieldCheck size={16} />
                Administrador
            </button>
        </div>

        <div className="p-8">
            <form onSubmit={handleLogin} className="space-y-5">
                <div>
                    <label className="block text-sm font-medium text-slate-700 mb-1.5">Email Corporativo</label>
                    <div className="relative rounded-xl shadow-sm">
                        <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none">
                            <User className="h-5 w-5 text-slate-400" />
                        </div>
                        <input 
                            type="email" 
                            value={email}
                            onChange={(e) => setEmail(e.target.value)}
                            className="block w-full pl-11 pr-4 py-3 sm:text-sm border-slate-200 rounded-xl focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-all bg-white"
                            placeholder={role === 'admin' ? 'admin@elevex.com' : 'tecnico@empresa.com'}
                        />
                    </div>
                </div>

                <div>
                    <label className="block text-sm font-medium text-slate-700 mb-1.5">Senha</label>
                    <div className="relative rounded-xl shadow-sm">
                        <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none">
                            <Lock className="h-5 w-5 text-slate-400" />
                        </div>
                        <input 
                            type="password" 
                            value={password}
                            onChange={(e) => setPassword(e.target.value)}
                            className="block w-full pl-11 pr-4 py-3 sm:text-sm border-slate-200 rounded-xl focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-all bg-white"
                            placeholder="••••••••"
                        />
                    </div>
                </div>

                <div className="pt-4">
                    <button 
                        type="submit" 
                        disabled={isLoading}
                        className={`w-full flex justify-center items-center py-3.5 px-4 border border-transparent rounded-xl shadow-lg text-sm font-bold text-white transition-all transform hover:-translate-y-0.5 ${role === 'admin' ? 'bg-slate-900 hover:bg-slate-800 shadow-slate-900/30' : 'bg-blue-600 hover:bg-blue-700 shadow-blue-500/30'}`}
                    >
                        {isLoading ? (
                            <span className="animate-pulse">Acessando...</span>
                        ) : (
                            <>Entrar no Sistema <ArrowRight className="ml-2 h-4 w-4" /></>
                        )}
                    </button>
                </div>
            </form>

            <div className="mt-6 text-center">
                <button onClick={onBack} className="text-sm font-medium text-slate-500 hover:text-blue-600 transition-colors">
                    Voltar para a página inicial
                </button>
            </div>
        </div>
        
        {/* Footer info for Demo */}
        <div className="bg-slate-50/80 p-4 text-center border-t border-slate-100">
            <p className="text-xs text-slate-500">
                <span className="font-semibold text-slate-700">Dica:</span> Use qualquer email/senha para testar o acesso {role === 'user' ? 'Técnico' : 'Admin'}.
            </p>
        </div>
      </div>
      </div>

      {/* Footer */}
      <footer className="relative z-10 border-t border-slate-200/50 py-6 mt-auto bg-white/50 backdrop-blur-sm">
        <div className="max-w-7xl mx-auto px-4 text-center">
          <p className="text-slate-500 text-sm font-medium">
            &copy; {new Date().getFullYear()} Elevex Tecnologia Ltda. Todos os direitos reservados.
          </p>
        </div>
      </footer>
    </div>
  );
};

export default Auth;
