import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { ThemeToggle } from "@/components/ThemeToggle";
import { Search, Download, Eye, Home, DollarSign, AlertCircle, ArrowLeft } from "lucide-react";
import { API_URL } from '../config';

function Lookup() {
  const navigate = useNavigate();
  const [billId, setBillId] = useState('');
  const [error, setError] = useState('');
  const [isDownloading, setIsDownloading] = useState(false);

  const viewBill = () => {
    if (!billId.trim()) {
      setError('Please enter a Bill ID');
      return;
    }
    navigate(`/result/${billId.trim()}`);
  };

  const downloadBill = async () => {
    if (!billId.trim()) {
      setError('Please enter a Bill ID');
      return;
    }

    setIsDownloading(true);
    try {
      const response = await axios.get(
        `${API_URL}/bill/${billId.trim()}/download`,
        { responseType: 'blob' }
      );

      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `bill_${billId}.jpg`);
      document.body.appendChild(link);
      link.click();
      link.remove();
      setIsDownloading(false);
    } catch (err) {
      setError('Bill not found or download failed');
      setIsDownloading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-indigo-50 via-white to-purple-50 dark:from-gray-950 dark:via-gray-900 dark:to-gray-950">
      {/* Top Navigation */}
      <nav className="border-b bg-white/50 dark:bg-gray-900/50 backdrop-blur-xl sticky top-0 z-40">
        <div className="container mx-auto px-4">
          <div className="flex items-center justify-between h-16">
            <div className="flex items-center gap-2">
              <div className="h-10 w-10 rounded-full bg-gradient-to-br from-indigo-600 to-purple-600 flex items-center justify-center">
                <DollarSign className="h-6 w-6 text-white" />
              </div>
              <h1 className="text-xl font-bold bg-gradient-to-r from-indigo-600 to-purple-600 dark:from-indigo-400 dark:to-purple-400 bg-clip-text text-transparent">
                PayUp
              </h1>
            </div>
            <ThemeToggle />
          </div>
        </div>
      </nav>

      {/* Main Content */}
      <div className="container mx-auto px-4 py-8">
        <div className="max-w-2xl mx-auto space-y-6">
          {/* Back Button */}
          <Button
            onClick={() => navigate('/')}
            variant="ghost"
            className="gap-2 mb-4"
          >
            <ArrowLeft className="h-4 w-4" />
            Back to Upload
          </Button>

          {/* Header */}
          <div className="text-center space-y-2">
            <div className="inline-flex h-16 w-16 items-center justify-center rounded-full bg-indigo-100 dark:bg-indigo-950 mb-4">
              <Search className="h-8 w-8 text-indigo-600 dark:text-indigo-400" />
            </div>
            <h2 className="text-3xl md:text-4xl font-bold text-gray-900 dark:text-white">
              Lookup Your Bill
            </h2>
            <p className="text-gray-600 dark:text-gray-400">
              Enter your Bill ID to view or download your split bill
            </p>
          </div>

          {/* Lookup Card */}
          <Card className="shadow-xl border-0 bg-white/80 dark:bg-gray-900/80 backdrop-blur-xl">
            <CardHeader className="border-b bg-gradient-to-r from-indigo-50 to-purple-50 dark:from-indigo-950/50 dark:to-purple-950/50">
              <CardTitle className="text-xl">Find Your Bill</CardTitle>
              <CardDescription>
                Bills are stored securely and can be accessed anytime with your unique ID
              </CardDescription>
            </CardHeader>
            
            <CardContent className="p-6 md:p-8">
              <div className="space-y-6">
                {error && (
                  <Alert variant="destructive">
                    <AlertCircle className="h-4 w-4" />
                    <AlertDescription>{error}</AlertDescription>
                  </Alert>
                )}
                
                <div className="space-y-2">
                  <Label htmlFor="bill_id" className="text-base font-semibold">
                    Bill ID
                  </Label>
                  <Input
                    type="text"
                    id="bill_id"
                    value={billId}
                    onChange={(e) => {
                      setBillId(e.target.value);
                      setError('');
                    }}
                    placeholder="e.g., 9e2db42e-ac21-467a-8011-b38af91db5fa"
                    className="h-12 font-mono text-sm"
                  />
                  <p className="text-xs text-gray-500 dark:text-gray-400">
                    You can find your Bill ID in the result page or from your previous session
                  </p>
                </div>
                
                <div className="grid sm:grid-cols-2 gap-4">
                  <Button 
                    onClick={viewBill} 
                    className="h-12 bg-gradient-to-r from-indigo-600 to-purple-600 hover:from-indigo-700 hover:to-purple-700 font-semibold shadow-lg shadow-indigo-500/30 dark:shadow-indigo-500/20"
                    size="lg"
                  >
                    <Eye className="h-5 w-5 mr-2" />
                    View Bill
                  </Button>
                  <Button 
                    onClick={downloadBill}
                    disabled={isDownloading}
                    className="h-12 bg-gradient-to-r from-green-600 to-emerald-600 hover:from-green-700 hover:to-emerald-700 font-semibold shadow-lg shadow-green-500/30 dark:shadow-green-500/20"
                    size="lg"
                  >
                    {isDownloading ? (
                      <>
                        <div className="h-5 w-5 border-2 border-white/30 border-t-white rounded-full animate-spin mr-2" />
                        Downloading...
                      </>
                    ) : (
                      <>
                        <Download className="h-5 w-5 mr-2" />
                        Download
                      </>
                    )}
                  </Button>
                </div>

                <div className="relative">
                  <div className="absolute inset-0 flex items-center">
                    <span className="w-full border-t border-gray-200 dark:border-gray-700" />
                  </div>
                  <div className="relative flex justify-center text-xs uppercase">
                    <span className="bg-white dark:bg-gray-900 px-2 text-gray-500 dark:text-gray-400">
                      Or
                    </span>
                  </div>
                </div>
                
                <Button 
                  onClick={() => navigate('/')} 
                  variant="outline"
                  className="w-full h-12 font-semibold border-2"
                  size="lg"
                >
                  <Home className="h-5 w-5 mr-2" />
                  Back to Home
                </Button>
              </div>
            </CardContent>
          </Card>

          {/* Info Card */}
          <Card className="border-0 bg-gradient-to-r from-indigo-50 to-purple-50 dark:from-indigo-950/30 dark:to-purple-950/30">
            <CardContent className="p-6">
              <div className="flex gap-4">
                <div className="flex-shrink-0">
                  <div className="h-10 w-10 rounded-full bg-indigo-100 dark:bg-indigo-900 flex items-center justify-center">
                    <AlertCircle className="h-5 w-5 text-indigo-600 dark:text-indigo-400" />
                  </div>
                </div>
                <div className="space-y-1">
                  <h3 className="font-semibold text-gray-900 dark:text-white">
                    Don't have a Bill ID?
                  </h3>
                  <p className="text-sm text-gray-600 dark:text-gray-400">
                    Upload a new bill to get started. Every processed bill receives a unique ID 
                    that you can use to access it later.
                  </p>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}

export default Lookup;
