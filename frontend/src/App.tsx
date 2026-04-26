import { Route, Routes } from "react-router-dom";
import Layout from "./components/Layout";
import Analyze from "./pages/Analyze";
import Pipelines from "./pages/Pipelines";
import Models from "./pages/Models";
import Health from "./pages/Health";
import Manual from "./pages/Manual";

export default function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route index element={<Analyze />} />
        <Route path="/pipelines" element={<Pipelines />} />
        <Route path="/models" element={<Models />} />
        <Route path="/health" element={<Health />} />
        <Route path="/manual" element={<Manual />} />
      </Route>
    </Routes>
  );
}
