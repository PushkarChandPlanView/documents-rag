import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { QueryClientProvider } from "@tanstack/react-query";
import { IntlProvider } from "react-intl";
import toolbarMessages from "@planview/pv-toolbar/lang/en.json";
import gridMessages from "@planview/pv-grid/lang/en.json";
import filterMessages from "@planview/pv-filter/lang/en.json";
import uikitMessages from "@planview/pv-uikit/lang/en.json";
import detailsMessages from "@planview/pv-details/lang/en.json";
import { queryClient } from "@/store/queryClient";
import { ProtectedRoute } from "@/auth/ProtectedRoute";
import Login from "@/pages/Login";
import Overview from "@/pages/Overview";
import Documents from "@/pages/Documents";
import { Compliance } from "@/pages/Compliance";
import { SearchBar } from "./components/search/SearchBar";
import SourceConfig from "./pages/SourceConfig";
import Layout from "./components/layout/Layout";

export default function App() {
  return (
    <IntlProvider locale={navigator.language} defaultLocale="en" messages={{ ...toolbarMessages, ...gridMessages, ...filterMessages, ...uikitMessages, ...detailsMessages }}>
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Routes>
          <Route path="/login" element={<Login />} />
          <Route element={<Layout />}>
            <Route element={<ProtectedRoute />}>
              <Route path="/" element={<Overview />} />
              <Route path="/documents" element={<Documents />} />
              <Route path="/documents/:docId" element={<Documents />} />
              <Route path="/search" element={<SearchBar />} />
              <Route path="/folders/:folderId" element={<Documents />} />
              <Route path="/folders/:folderId/:docId" element={<Documents />} />
              <Route path="/compliance" element={<Compliance />} />
              <Route path="/sources" element={<SourceConfig />} />
            </Route>
            <Route path="*" element={<Navigate to="/" replace />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
    </IntlProvider>
  );
}
